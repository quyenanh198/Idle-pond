extends GutTest

const PondView := preload("res://scripts/pond/pond_view.gd")


func _sum(d: Dictionary) -> int:
	var n := 0
	for v in d.values():
		n += int(v)
	return n


func test_under_cap_renders_everything():
	assert_eq(PondView.render_counts({"guppy": 3, "snail": 2}, 40), {"guppy": 3, "snail": 2})


func test_over_cap_fills_cap_and_keeps_every_species():
	var owned := {"guppy": 1000, "snail": 1, "goldfish": 1, "tetra": 1, "catfish": 1, "angelfish": 1, "koi": 1, "arowana": 1}
	var r := PondView.render_counts(owned, 40)
	assert_eq(_sum(r), 40)
	for id in owned:
		assert_gte(int(r[id]), 1, id)
	assert_gt(int(r.guppy), int(r.snail))


func test_zero_counts_skipped():
	var r := PondView.render_counts({"guppy": 50, "snail": 0}, 40)
	assert_false(r.has("snail"))
	assert_eq(_sum(r), 40)
