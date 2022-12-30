from __future__ import annotations

import model
from model import OrderLine
from repository import AbstractRepository


class InvalidSku(ValueError):
    pass


class UnallocatedLine(ValueError):
    pass


def is_valid_sku(sku, batches):
    return sku in {b.sku for b in batches}


def allocate(line: OrderLine, repo: AbstractRepository, session) -> str:
    batches = repo.list()
    if not is_valid_sku(line.sku, batches):
        raise InvalidSku(f"Invalid sku {line.sku}")
    batchref = model.allocate(line, batches)
    session.commit()
    return batchref


def add_batch(ref: str, sku: str, qty: int,
              eta, repo: AbstractRepository, session) -> None:
    repo.add(
        model.Batch(ref, sku, qty, eta)
    )
    session.commit()


def deallocate(orderid: str, sku: str,
               repo: AbstractRepository, session):
    batches = [
        b for b in repo.list() if b.sku == sku
    ]
    try:
        batch = next(b for b in batches if b.has_line(orderid))
        batch.deallocate_orderid(orderid)
    except StopIteration:
        raise UnallocatedLine(f"Line with id {orderid} has not been allocated")

    session.commit()
