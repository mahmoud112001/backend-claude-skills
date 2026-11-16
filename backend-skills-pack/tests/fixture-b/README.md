# Stockroom

Stockroom is a small inventory service for a company with a few warehouses. Other systems call it over gRPC. It has no UI: the prototype is this README plus the stub in `proto/` and `internal/`.

## What it must do

1. Warehouse staff register products by SKU (code, name, unit of measure).
2. Staff register warehouses and the bin locations inside them.
3. Staff receive goods: a goods receipt adds quantity of a SKU to a bin.
4. An outside system asks to reserve a quantity of a SKU for an outbound shipment. The reservation succeeds only if enough unreserved stock exists in one warehouse; otherwise it fails with a clear reason.
5. The outside system can release a reservation it no longer needs.
6. When the shipment is picked, the reserved quantity leaves the stock.
7. After a cycle count, staff adjust the quantity of a SKU in a bin, with a reason code.
8. Each SKU can have a low-stock threshold per warehouse. When available quantity drops below it, a reorder suggestion is raised automatically for the purchasing team; staff never create suggestions by hand.
9. Purchasing can accept or dismiss a reorder suggestion.
10. Anyone with read access can ask how much of a SKU is on hand, reserved and available, per warehouse.

Stock never goes negative. A reservation expires after a time the business still has to decide.

## Tech

- Go 1.22, gRPC (see `proto/stockroom/v1/stockroom.proto`)
- Database and broker: see `docker-compose.yml`
- Rules: [ARCHITECTURE.md](ARCHITECTURE.md)
- Design docs and diagrams: PlantUML (`docs/*.puml`)
