extends GutTest

const GameStateScript := preload("res://scripts/autoload/game_state.gd")

var gs
var guppy: SpeciesData
var snail: SpeciesData


func before_each():
	gs = autofree(GameStateScript.new())
	guppy = SpeciesCatalog.by_id("guppy")
	snail = SpeciesCatalog.by_id("snail")


func test_new_game_defaults():
	assert_eq(gs.coins, 15.0)
	assert_eq(gs.level(), 1)
	assert_eq(gs.total_fish(), 0)
	assert_eq(gs.capacity(), 10)


func test_buy_spends_coins_and_gives_xp():
	assert_true(gs.buy(guppy))
	assert_eq(gs.coins, 5.0)
	assert_eq(gs.xp, 10.0)
	assert_eq(gs.owned_count(guppy), 1)
	assert_almost_eq(gs.fish_cost(guppy), 11.5, 0.0001)


func test_cannot_buy_locked_or_unaffordable():
	gs.coins = 1e9
	assert_false(gs.buy(snail), "snail locked at level 1")
	gs.coins = 1.0
	assert_false(gs.buy(guppy))


func test_capacity_limits_buying():
	gs.coins = 1e9
	for i in 10:
		assert_true(gs.buy(guppy))
	assert_false(gs.buy(guppy))


func test_sell_refunds_half_and_keeps_xp():
	gs.buy(guppy)
	var xp_before: float = gs.xp
	assert_true(gs.sell(guppy))
	assert_eq(gs.coins, 10.0)
	assert_eq(gs.xp, xp_before)
	assert_false(gs.sell(guppy))


func test_level_up_signal_and_unlock():
	watch_signals(gs)
	gs.coins = 1000.0
	gs.upgrade(Balance.POND_SIZE)  # 100 coins -> 100 xp -> level 2
	assert_signal_emitted_with_parameters(gs, "leveled_up", [2])
	assert_true(gs.is_unlocked(snail))


func test_first_purchase_signal_only_from_zero():
	watch_signals(gs)
	gs.coins = 1000.0
	gs.buy(guppy)
	gs.buy(guppy)
	assert_signal_emit_count(gs, "species_first_bought", 1)


func test_upgrades_apply_and_max_out():
	gs.coins = 1e12
	assert_true(gs.upgrade(Balance.POND_SIZE))
	assert_eq(gs.capacity(), 15)
	assert_true(gs.upgrade(Balance.BETTER_FOOD))
	gs.owned = {"guppy": 2}
	assert_almost_eq(gs.income_per_sec(), 2 * 0.5 * 1.25, 0.0001)
	for i in 11:
		gs.coins = 1e12
		assert_true(gs.upgrade(Balance.DEEP_SLEEP))
	gs.coins = 1e12
	assert_false(gs.upgrade(Balance.DEEP_SLEEP))
	assert_eq(gs.offline_cap_sec(), 86400.0)


func test_apply_offline_is_capped_and_counts_lifetime():
	gs.owned = {"guppy": 2}
	var earned: float = gs.apply_offline(100000.0)
	assert_eq(earned, 1.0 * 7200.0)
	assert_eq(gs.lifetime_coins, 7200.0)
	assert_eq(gs.apply_offline(-5.0), 0.0)


func test_dict_round_trip_and_unknown_species_dropped():
	gs.coins = 1e9
	gs.buy(guppy)
	gs.upgrade(Balance.BETTER_FOOD)
	var d: Dictionary = gs.to_dict()
	d.owned["shark"] = 3
	var other = autofree(GameStateScript.new())
	other.load_dict(JSON.parse_string(JSON.stringify(d)))
	assert_eq(other.coins, gs.coins)
	assert_eq(other.xp, gs.xp)
	assert_eq(other.owned, {"guppy": 1})
	assert_eq(other.upgrade_level(Balance.BETTER_FOOD), 1)
	assert_eq(typeof(other.owned["guppy"]), TYPE_INT)
