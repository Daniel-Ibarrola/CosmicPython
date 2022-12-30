import pytest
import model
import repository
import services


class FakeRepository(repository.AbstractRepository):
    def __init__(self, batches):
        self._batches = set(batches)

    def add(self, batch):
        self._batches.add(batch)

    def get(self, reference):
        return next(b for b in self._batches if b.reference == reference)

    def list(self):
        return list(self._batches)


class FakeSession:
    committed = False

    def commit(self):
        self.committed = True


def test_returns_allocation():
    line = model.OrderLine("o1", "COMPLICATED-LAMP", 10)
    batch = model.Batch("b1", "COMPLICATED-LAMP", 100, eta=None)
    repo = FakeRepository([batch])

    result = services.allocate(line, repo, FakeSession())
    assert result == "b1"


def test_error_for_invalid_sku():
    line = model.OrderLine("o1", "NONEXISTENTSKU", 10)
    batch = model.Batch("b1", "AREALSKU", 100, eta=None)
    repo = FakeRepository([batch])

    with pytest.raises(services.InvalidSku, match="Invalid sku NONEXISTENTSKU"):
        services.allocate(line, repo, FakeSession())


def test_commits():
    line = model.OrderLine("o1", "OMINOUS-MIRROR", 10)
    batch = model.Batch("b1", "OMINOUS-MIRROR", 100, eta=None)
    repo = FakeRepository([batch])
    session = FakeSession()

    services.allocate(line, repo, session)
    assert session.committed is True


def test_deallocate_increments_available_quantity():
    repo, session = FakeRepository([]), FakeSession()
    services.add_batch("b1", "BLUE-PLINTH", 100, None, repo, session)
    line = model.OrderLine("o1", "BLUE-PLINTH", 10)
    services.allocate(line, repo, session)
    batch = repo.get(reference="b1")
    assert batch.available_quantity == 90

    services.deallocate(line.orderid, line.sku, repo, session)
    assert batch.available_quantity == 100


def test_deallocate_increments_correct_quantity():
    repo, session = FakeRepository([]), FakeSession()
    services.add_batch("b1", "BLUE-PLINTH", 100, None, repo, session)
    services.add_batch("r1", "RED-CHAIR", 100, None, repo, session)

    line_1 = model.OrderLine("o1", "BLUE-PLINTH", 10)
    line_2 = model.OrderLine("o2", "RED-CHAIR", 5)
    services.allocate(line_1, repo, session)
    services.allocate(line_2, repo, session)

    services.deallocate(line_2.orderid, line_2.sku, repo, session)

    batch_1 = repo.get(reference="b1")
    batch_2 = repo.get(reference="r1")
    assert batch_1.available_quantity == 90
    assert batch_2.available_quantity == 100


def test_trying_to_deallocate_unallocated_batch():
    batch = model.Batch("b1", "AREALSKU", 100, eta=None)
    repo = FakeRepository([batch])
    session = FakeSession()

    unallocated_line = model.OrderLine("o1", "AREALSKU", 10)
    with pytest.raises(services.UnallocatedLine,
                       match="Line with id o1 has not been allocated"):
        services.deallocate(
            unallocated_line.orderid, unallocated_line.sku, repo, session
        )
