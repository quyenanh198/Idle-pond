extends GutTest
## Greedy player with 4 ten-minute check-ins a day and 8 h sleep (spec section 3).

const GameStateScript := preload("res://scripts/autoload/game_state.gd")
const DAY := 86400.0
const STEP := 10.0
const SESSION_STEPS := 60
const AWAY_SEC := 3.0 * 3600.0 + 50.0 * 60.0
const NIGHT_SEC := 8.0 * 3600.0

var gs


func before_each():
	gs = autofree(GameStateScript.new())


func test_pacing_targets():
	var r := _simulate(10.0)
	gut.p("level 2 at %ds, level 15 at %.2f days" % [r.level2_at, r.level15_at / DAY])
	assert_between(r.level2_at, 1.0, 120.0, "first new species within 2 minutes")
	assert_between(r.level15_at, 3.0 * DAY, 5.0 * DAY, "all species within 3-5 days")


func _simulate(max_days: float) -> Dictionary:
	var t := 0.0
	var level2_at := -1.0
	while t < max_days * DAY:
		for k in 4:
			for i in SESSION_STEPS:
				_shop()
				gs.earn(gs.income_per_sec() * STEP)
				t += STEP
				if level2_at < 0.0 and gs.level() >= 2:
					level2_at = t
				if gs.level() >= 15:
					return {"level2_at": level2_at, "level15_at": t}
			var away := AWAY_SEC + (NIGHT_SEC if k == 3 else 0.0)
			gs.apply_offline(away)
			t += away
	return {"level2_at": level2_at, "level15_at": -1.0}


func _shop() -> void:
	while true:
		var deep_cost: float = gs.upgrade_cost(Balance.DEEP_SLEEP)
		if gs.can_upgrade(Balance.DEEP_SLEEP) and deep_cost <= gs.coins * 0.25:
			gs.upgrade(Balance.DEEP_SLEEP)
			continue
		var best := _best_action()
		if best.is_empty() or gs.coins < best.price:
			return
		best.run.call()


## The action with the best income gain per coin: {value, price, run}.
func _best_action() -> Dictionary:
	var fm := Economy.food_multiplier(gs.upgrade_level(Balance.BETTER_FOOD))
	var full: bool = gs.total_fish() >= gs.capacity()
	var best := {}
	var top: SpeciesData = null
	for s in SpeciesCatalog.all():
		if not gs.is_unlocked(s):
			continue
		top = s
		var cost: float = gs.fish_cost(s)
		if not full:
			best = _better(best, s.coins_per_sec * fm / cost, cost, func(): gs.buy(s))
			continue
		var worst := _worst_owned()
		if worst == null or worst.coins_per_sec >= s.coins_per_sec:
			continue
		var net: float = cost - gs.sell_refund(worst)
		var gain := (s.coins_per_sec - worst.coins_per_sec) * fm
		best = _better(best, gain / maxf(net, 1.0), net, func():
			gs.sell(worst)
			gs.buy(s))
	var income: float = gs.income_per_sec()
	if income > 0.0:
		var food_cost: float = gs.upgrade_cost(Balance.BETTER_FOOD)
		var food_gain := income * Balance.FOOD_BONUS_PER_LEVEL / fm
		best = _better(best, food_gain / food_cost, food_cost, func(): gs.upgrade(Balance.BETTER_FOOD))
	if full and top != null:
		var pond_cost: float = gs.upgrade_cost(Balance.POND_SIZE)
		var value: float = top.coins_per_sec * fm / (pond_cost + gs.fish_cost(top))
		best = _better(best, value, pond_cost, func(): gs.upgrade(Balance.POND_SIZE))
	return best


func _better(best: Dictionary, value: float, price: float, run: Callable) -> Dictionary:
	if best.is_empty() or value > best.value:
		return {"value": value, "price": price, "run": run}
	return best


func _worst_owned() -> SpeciesData:
	for s in SpeciesCatalog.all():
		if gs.owned_count(s) > 0:
			return s
	return null
