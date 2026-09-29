from dataclasses import dataclass

from django.db import transaction

from ordersync_lab.orders.models import (
    Order,
    StockMovement,
    WarehouseFailurePlan,
    WarehouseReservation,
    WarehouseStock,
)


class RetryableWarehouseError(Exception):
    def __init__(self, error_code: str):
        self.error_code = error_code
        super().__init__(error_code)


@dataclass(frozen=True)
class ReservationLineResult:
    sku: str
    remaining_quantity: int


@dataclass(frozen=True)
class ReservationResult:
    accepted: bool
    failure_reason: str = ""
    lines: tuple[ReservationLineResult, ...] = ()


class FakeAtlasWarehouse:
    """A deterministic, idempotent local implementation of the warehouse boundary."""

    def reserve(self, order_id) -> ReservationResult:
        retryable_error = ""

        with transaction.atomic():
            existing = (
                WarehouseReservation.objects.select_for_update().filter(order_id=order_id).first()
            )
            if existing:
                return self._stored_result(existing)

            order = Order.objects.prefetch_related("items").get(pk=order_id)
            failure_plan = (
                WarehouseFailurePlan.objects.select_for_update()
                .filter(external_order_id=order.external_order_id)
                .first()
            )
            if failure_plan and failure_plan.failures_remaining:
                failure_plan.failures_remaining -= 1
                failure_plan.save(update_fields=["failures_remaining", "updated_at"])
                retryable_error = failure_plan.error_code
            else:
                return self._reserve_stock(order)

        raise RetryableWarehouseError(retryable_error)

    def _reserve_stock(self, order: Order) -> ReservationResult:
        items = list(order.items.all())
        stock_by_sku = {
            stock.sku: stock
            for stock in WarehouseStock.objects.select_for_update().filter(
                sku__in=[item.sku for item in items]
            )
        }

        if len(stock_by_sku) != len(items):
            return self._store_rejection(order, "unknown_sku")

        if any(stock_by_sku[item.sku].available_quantity < item.quantity for item in items):
            return self._store_rejection(order, "insufficient_stock")

        reservation = WarehouseReservation.objects.create(
            order=order,
            status=WarehouseReservation.Status.ACCEPTED,
        )
        line_results = []
        for item in items:
            stock = stock_by_sku[item.sku]
            stock.available_quantity -= item.quantity
            stock.save(update_fields=["available_quantity", "updated_at"])
            StockMovement.objects.create(
                reservation=reservation,
                sku=item.sku,
                quantity=item.quantity,
                remaining_quantity=stock.available_quantity,
            )
            line_results.append(
                ReservationLineResult(
                    sku=item.sku,
                    remaining_quantity=stock.available_quantity,
                )
            )

        return ReservationResult(accepted=True, lines=tuple(line_results))

    def _store_rejection(self, order: Order, reason: str) -> ReservationResult:
        WarehouseReservation.objects.create(
            order=order,
            status=WarehouseReservation.Status.REJECTED,
            failure_reason=reason,
        )
        return ReservationResult(accepted=False, failure_reason=reason)

    def _stored_result(self, reservation: WarehouseReservation) -> ReservationResult:
        if reservation.status == WarehouseReservation.Status.REJECTED:
            return ReservationResult(accepted=False, failure_reason=reservation.failure_reason)

        lines = tuple(
            ReservationLineResult(
                sku=movement.sku,
                remaining_quantity=movement.remaining_quantity,
            )
            for movement in reservation.movements.order_by("sku")
        )
        return ReservationResult(accepted=True, lines=lines)
