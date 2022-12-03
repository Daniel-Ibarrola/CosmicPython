from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class OrderLine:
    orderid: str
    sku: str
    qty: int


class Batch:

    def __init__(
            self, ref: str, sku: str, qty: int, eta: Optional[date]
    ):
        self.reference = ref
        self.sku = sku
        self.eta = eta
        self._purchased_quantity = qty
        self._allocations = set()  # type: set[OrderLine]

    def allocate(self, line: OrderLine) -> None:
        """ Allocate a new order line to the batch. """
        if line not in self._allocations:
            self._allocations.add(line)

    def deallocate(self, line: OrderLine) -> None:
        """ Deallocate a line from the batch. """
        if line in self._allocations:
            self._allocations.remove(line)

    @property
    def allocated_quantity(self) -> int:
        return sum(line.qty for line in self._allocations)

    @property
    def available_quantity(self) -> int:
        return self._purchased_quantity - self.allocated_quantity

    def can_allocate(self, line: OrderLine) -> bool:
        """ Check if an order line can be allocated. This means
            that the line sku must match the batch's one and
            the quantity must be smaller or equal to the available in
            the batch.
        """
        return line.sku == self.sku and line.qty <= self.available_quantity

    def __eq__(self, other):
        if isinstance(other, Batch):
            return other.reference == self.reference
        return False

    def __gt__(self, other):
        if self.eta is None:
            return False
        if other.eta is None:
            return True
        return self.eta > other.eta

    def __hash__(self):
        return hash(self.reference)


class OutOfStock(ValueError):
    pass


def allocate(line: OrderLine, batches: list[Batch]) -> str:
    """ Allocate an order line to the most suitable batch in a list
        of batches.
    """
    try:
        batch = next(b for b in sorted(batches) if b.can_allocate(line))
    except StopIteration:
        raise OutOfStock(f"Out of stock for {line.sku}")

    batch.allocate(line)
    return batch.reference

