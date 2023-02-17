from datetime import datetime
from flask import Flask, request

from allocation.domain import commands
from allocation.adapters import orm
from allocation.service_layer import messagebus, unit_of_work
from allocation.service_layer.handlers import InvalidSku

app = Flask(__name__)
orm.start_mappers()


@app.route("/add_batch", methods=["POST"])
def add_batch():
    eta = request.json["eta"]
    if eta is not None:
        eta = datetime.fromisoformat(eta).date()
    command = commands.CreateBatch(
        request.json["ref"], request.json["sku"], request.json["qty"], eta
    )
    messagebus.handle(command, unit_of_work.SqlAlchemyUnitOfWork())
    return "OK", 201


@app.route("/allocate", methods=["POST"])
def allocate_endpoint():
    try:
        command = commands.Allocate(
            request.json["orderid"], request.json["sku"], request.json["qty"]
        )
        results = messagebus.handle(command, unit_of_work.SqlAlchemyUnitOfWork())
        batchref = results.pop(0)
    except InvalidSku as e:
        return {"message": str(e)}, 400

    return {"batchref": batchref}, 201
