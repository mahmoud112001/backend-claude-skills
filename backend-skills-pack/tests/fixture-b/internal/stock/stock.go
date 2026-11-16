// Package stock is a prototype sketch, not production code.
package stock

import "github.com/oklog/ulid/v2"

// StockLevel is the quantity of one SKU in one bin.
type StockLevel struct {
	ID       ulid.ULID
	SKU      string
	BinID    ulid.ULID
	OnHand   int64
	Reserved int64
}

// Available is what can still be reserved.
func (s StockLevel) Available() int64 { return s.OnHand - s.Reserved }
