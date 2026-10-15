class_name Balance
## Tuning numbers not tied to a single species. See spec section 3.

const START_COINS := 15.0
const FISH_COST_GROWTH := 1.15
const SELL_REFUND_RATIO := 0.5
const XP_BASE := 50.0
const XP_GROWTH := 3.5
const FOOD_BONUS_PER_LEVEL := 0.25
const POND_BASE_CAPACITY := 10
const POND_CAPACITY_PER_LEVEL := 5
const OFFLINE_BASE_CAP_SEC := 7200.0
const OFFLINE_CAP_PER_LEVEL_SEC := 7200.0
const MAX_RENDERED_FISH := 40

const POND_SIZE := "pond_size"
const BETTER_FOOD := "better_food"
const DEEP_SLEEP := "deep_sleep"

## max_level -1 means unlimited.
const UPGRADES := {
	POND_SIZE: {"name": "Pond Size", "base_cost": 100.0, "growth": 3.0, "max_level": -1},
	BETTER_FOOD: {"name": "Better Food", "base_cost": 500.0, "growth": 4.0, "max_level": -1},
	DEEP_SLEEP: {"name": "Deep Sleep", "base_cost": 1000.0, "growth": 5.0, "max_level": 11},
}
