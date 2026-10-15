extends GutTest


func test_has_eight_species_sorted_by_unlock_level():
	var levels := SpeciesCatalog.all().map(func(s): return s.unlock_level)
	assert_eq(levels, [1, 2, 3, 5, 7, 9, 12, 15])


func test_ids_unique_and_lookup_works():
	var ids := {}
	for s in SpeciesCatalog.all():
		ids[s.id] = true
	assert_eq(ids.size(), 8)
	assert_eq(SpeciesCatalog.by_id("koi").display_name, "Koi")
	assert_null(SpeciesCatalog.by_id("shark"))


func test_each_tier_earns_more_per_fish_and_costs_more():
	var all := SpeciesCatalog.all()
	for i in range(1, all.size()):
		assert_gt(all[i].coins_per_sec, all[i - 1].coins_per_sec, all[i].id)
		assert_gt(all[i].base_cost, all[i - 1].base_cost, all[i].id)


func test_spec_values():
	var g := SpeciesCatalog.by_id("guppy")
	assert_eq(g.base_cost, 10.0)
	assert_eq(g.coins_per_sec, 0.5)
	assert_eq(g.zone, SpeciesData.Zone.SURFACE)
	var a := SpeciesCatalog.by_id("arowana")
	assert_eq(a.base_cost, 930000000.0)
	assert_eq(a.coins_per_sec, 300.0)
