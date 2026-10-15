class_name Economy
## Pure economy formulas. No state; see spec section 3.


static func fish_cost(base_cost: float, owned: int) -> float:
	return base_cost * pow(Balance.FISH_COST_GROWTH, owned)


## Refund for selling one fish: half of what the most recent one cost.
static func sell_refund(base_cost: float, owned: int) -> float:
	if owned <= 0:
		return 0.0
	return Balance.SELL_REFUND_RATIO * fish_cost(base_cost, owned - 1)


static func food_multiplier(food_level: int) -> float:
	return 1.0 + Balance.FOOD_BONUS_PER_LEVEL * food_level


static func income_per_sec(owned: Dictionary, species: Array[SpeciesData], food_level: int) -> float:
	var base := 0.0
	for s in species:
		base += int(owned.get(s.id, 0)) * s.coins_per_sec
	return base * food_multiplier(food_level)


static func capacity(pond_level: int) -> int:
	return Balance.POND_BASE_CAPACITY + Balance.POND_CAPACITY_PER_LEVEL * pond_level


static func offline_cap_sec(deep_sleep_level: int) -> float:
	return Balance.OFFLINE_BASE_CAP_SEC + Balance.OFFLINE_CAP_PER_LEVEL_SEC * deep_sleep_level


static func offline_earnings(income: float, elapsed_sec: float, cap_sec: float) -> float:
	return income * clampf(elapsed_sec, 0.0, cap_sec)


static func xp_to_next(level: int) -> float:
	return Balance.XP_BASE * pow(Balance.XP_GROWTH, level - 1)


## Returns {"level": int, "into": float, "needed": float}.
static func level_progress(total_xp: float) -> Dictionary:
	var level := 1
	var rest := total_xp
	while rest >= xp_to_next(level):
		rest -= xp_to_next(level)
		level += 1
	return {"level": level, "into": rest, "needed": xp_to_next(level)}


static func upgrade_cost(id: String, level: int) -> float:
	var u: Dictionary = Balance.UPGRADES[id]
	return u.base_cost * pow(u.growth, level)


static func upgrade_maxed(id: String, level: int) -> bool:
	var max_level: int = Balance.UPGRADES[id].max_level
	return max_level >= 0 and level >= max_level
