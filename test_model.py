from datetime import date, timedelta
import pytest

from model import Batch, OrderLine, allocate, OutOfStock

today = date.today()
tomorrow = today + timedelta(days=1)
later = tomorrow + timedelta(days=10)


def make_batch_and_line(sku, batch_qty, line_qty):
    return (
        Batch("batch-001", sku, batch_qty, eta=today),
        OrderLine("order-ref", sku, line_qty)
    )


def test_allocating_to_a_batch_reduces_the_available_quantity():
    batch, line = make_batch_and_line("SMALL-TABLE", 20, 2)
    batch.allocate(line)
    assert batch.available_quantity == 18


def test_can_allocate_if_available_greater_than_required():
    batch, line = make_batch_and_line("ELEGANT-LAMP", 20, 2)
    assert batch.can_allocate(line)


def test_cannot_allocate_if_available_smaller_than_required():
    batch, line = make_batch_and_line("BLUE-CUSHION", 1, 2)
    assert not batch.can_allocate(line)


def test_can_allocate_if_available_equal_to_required():
    batch, line = make_batch_and_line("SMALL-TABLE", 20, 20)
    assert batch.can_allocate(line)


def test_cannot_allocate_if_skus_dont_match():
    batch = Batch("batch-001", "UNCOMFORTABLE-CHAIR", 5, eta=None)
    different_sku_line = OrderLine("order-ref", "EXPENSIVE-TOASTER", 2)
    assert not batch.can_allocate(different_sku_line)


def test_can_only_deallocate_allocated_lines():
    batch, unallocated_line = make_batch_and_line("DECORATIVE-TRINKET", 20, 2)
    batch.deallocate(unallocated_line)
    assert batch.available_quantity == 20


def test_deallocating_reduces_allocated_quantity():
    batch, line = make_batch_and_line("SMALL-TABLE", 10, 2)
    batch.allocate(line)
    assert batch.allocated_quantity == 2

    batch.deallocate(line)
    assert batch.allocated_quantity == 0


def test_deallocating_increases_available_quantity():
    batch, line = make_batch_and_line("SMALL-TABLE", 10, 2)
    batch.allocate(line)
    assert batch.available_quantity == 8

    batch.deallocate(line)
    assert batch.available_quantity == 10


def test_allocation_is_idempotent():
    batch, line = make_batch_and_line("ANGULAR-DESK", 20, 2)
    batch.allocate(line)
    batch.allocate(line)
    assert batch.available_quantity == 18


def test_batch_equality():
    batch = Batch("batch-001", "UNCOMFORTABLE-CHAIR", 5, eta=None)
    assert batch == Batch("batch-001", "UNCOMFORTABLE-CHAIR", 5, eta=None)
    assert not batch == Batch("batch-002", "UNCOMFORTABLE-CHAIR", 5, eta=None)


def test_prefers_in_stock_batches_to_shipments():
    in_stock_batch = Batch("in-stock", "RETRO-CLOCK", 10, eta=None)
    shipment_batch = Batch("shipment", "RETRO-CLOCK", 10, eta=tomorrow)
    line = OrderLine("oref", "RETRO-CLOCK", 5)

    allocate(line, [in_stock_batch, shipment_batch])

    assert in_stock_batch.available_quantity == 5
    assert shipment_batch.available_quantity == 10


def test_prefers_earlier_batches():
    earliest = Batch("early", "MINIMALIST-SPOON", 100, eta=today)
    middle = Batch("early", "MINIMALIST-SPOON", 100, eta=tomorrow)
    latest = Batch("early", "MINIMALIST-SPOON", 100, eta=later)
    line = OrderLine("oref", "MINIMALIST-SPOON", 10)

    allocate(line, [middle, earliest, latest])

    assert earliest.available_quantity == 90
    assert middle.available_quantity == 100
    assert latest.available_quantity == 100


def test_returns_allocated_batch_ref():
    in_stock_batch = Batch("in-stock-batch-ref", "RETRO-CLOCK", 10, eta=None)
    shipment_batch = Batch("shipment-batch-ref", "RETRO-CLOCK", 10, eta=tomorrow)
    line = OrderLine("oref", "RETRO-CLOCK", 5)
    allocation = allocate(line, [in_stock_batch, shipment_batch])
    assert allocation == in_stock_batch.reference


def test_raises_out_of_stock_exception_if_cannot_allocate():
    batch = Batch("batch1", "SMALL-FORK", 10, eta=today)
    allocate(OrderLine("order1", "SMALL-FORK", 10), [batch])

    with pytest.raises(OutOfStock, match="SMALL-FORK"):
        allocate(OrderLine("order1", "SMALL-FORK", 1), [batch])
