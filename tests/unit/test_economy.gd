extends GutTest


func test_fish_cost_grows_15_percent():
	assert_almost_eq(Economy.fish_cost(10.0, 0), 10.0, 0.0001)
	assert_almost_eq(Economy.fish_cost(10.0, 2), 13.225, 0.0001)


func test_sell_refund_is_half_of_last_price():
	assert_eq(Economy.sell_refund(10.0, 0), 0.0)
	assert_almost_eq(Economy.sell_refund(10.0, 1), 5.0, 0.0001)
	assert_almost_eq(Economy.sell_refund(10.0, 3), 0.5 * 13.225, 0.0001)


func test_income_sums_species_times_food():
	var species := SpeciesCatalog.all()
	var owned := {"guppy": 4, "snail": 2, "unknown": 9}
	assert_almost_eq(Economy.income_per_sec(owned, species, 0), 4 * 0.5 + 2 * 1.25, 0.0001)
	assert_almost_eq(Economy.income_per_sec(owned, species, 2), (4 * 0.5 + 2 * 1.25) * 1.5, 0.0001)


func test_capacity_and_offline_cap():
	assert_eq(Economy.capacity(0), 10)
	assert_eq(Economy.capacity(3), 25)
	assert_eq(Economy.offline_cap_sec(0), 7200.0)
	assert_eq(Economy.offline_cap_sec(11), 86400.0)


func test_offline_earnings_clamped():
	assert_eq(Economy.offline_earnings(2.0, 100.0, 7200.0), 200.0)
	assert_eq(Economy.offline_earnings(2.0, 99999.0, 7200.0), 14400.0)
	assert_eq(Economy.offline_earnings(2.0, -50.0, 7200.0), 0.0)


func test_level_curve():
	assert_eq(Economy.xp_to_next(1), 50.0)
	assert_almost_eq(Economy.xp_to_next(3), 50.0 * 3.5 * 3.5, 0.0001)
	assert_eq(Economy.level_progress(0.0), {"level": 1, "into": 0.0, "needed": 50.0})
	assert_eq(Economy.level_progress(49.9).level, 1)
	assert_eq(Economy.level_progress(50.0).level, 2)
	var p := Economy.level_progress(50.0 + 175.0 + 10.0)
	assert_eq(p.level, 3)
	assert_almost_eq(p.into, 10.0, 0.0001)


func test_upgrade_costs_and_max():
	assert_eq(Economy.upgrade_cost(Balance.POND_SIZE, 0), 100.0)
	assert_eq(Economy.upgrade_cost(Balance.POND_SIZE, 2), 900.0)
	assert_eq(Economy.upgrade_cost(Balance.BETTER_FOOD, 1), 2000.0)
	assert_eq(Economy.upgrade_cost(Balance.DEEP_SLEEP, 1), 5000.0)
	assert_false(Economy.upgrade_maxed(Balance.DEEP_SLEEP, 10))
	assert_true(Economy.upgrade_maxed(Balance.DEEP_SLEEP, 11))
	assert_false(Economy.upgrade_maxed(Balance.POND_SIZE, 500))
