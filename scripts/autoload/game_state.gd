extends Node
## Player progress and actions. Autoloaded as `GameState`.

signal changed
signal leveled_up(level: int)
signal species_first_bought(species_id: String)

var coins: float
var xp: float
var lifetime_coins: float
var owned: Dictionary  # species id -> int
var upgrades: Dictionary  # upgrade id -> int
## Income ticks in _process only while true (set by SaveService once loaded).
var running := false


func _init() -> void:
	_set_defaults()


func reset() -> void:
	_set_defaults()
	changed.emit()


func _process(delta: float) -> void:
	if running:
		earn(income_per_sec() * delta)


func level() -> int:
	return Economy.level_progress(xp).level


func level_progress() -> Dictionary:
	return Economy.level_progress(xp)


func total_fish() -> int:
	var n := 0
	for c in owned.values():
		n += int(c)
	return n


func capacity() -> int:
	return Economy.capacity(upgrades[Balance.POND_SIZE])


func income_per_sec() -> float:
	return Economy.income_per_sec(owned, SpeciesCatalog.all(), upgrades[Balance.BETTER_FOOD])


func offline_cap_sec() -> float:
	return Economy.offline_cap_sec(upgrades[Balance.DEEP_SLEEP])


func owned_count(s: SpeciesData) -> int:
	return int(owned.get(s.id, 0))


func is_unlocked(s: SpeciesData) -> bool:
	return level() >= s.unlock_level


func fish_cost(s: SpeciesData) -> float:
	return Economy.fish_cost(s.base_cost, owned_count(s))


func sell_refund(s: SpeciesData) -> float:
	return Economy.sell_refund(s.base_cost, owned_count(s))


func can_buy(s: SpeciesData) -> bool:
	return is_unlocked(s) and total_fish() < capacity() and coins >= fish_cost(s)


func buy(s: SpeciesData) -> bool:
	if not can_buy(s):
		return false
	var first := owned_count(s) == 0
	_spend(fish_cost(s))
	owned[s.id] = owned_count(s) + 1
	if first:
		species_first_bought.emit(s.id)
	changed.emit()
	return true


## Refunds are not earnings, so lifetime_coins is unchanged.
func sell(s: SpeciesData) -> bool:
	if owned_count(s) <= 0:
		return false
	coins += sell_refund(s)
	owned[s.id] = owned_count(s) - 1
	changed.emit()
	return true


func upgrade_level(id: String) -> int:
	return upgrades[id]


func upgrade_cost(id: String) -> float:
	return Economy.upgrade_cost(id, upgrades[id])


func can_upgrade(id: String) -> bool:
	return not Economy.upgrade_maxed(id, upgrades[id]) and coins >= upgrade_cost(id)


func upgrade(id: String) -> bool:
	if not can_upgrade(id):
		return false
	_spend(upgrade_cost(id))
	upgrades[id] += 1
	changed.emit()
	return true


func earn(amount: float) -> void:
	coins += amount
	lifetime_coins += amount


func apply_offline(elapsed_sec: float) -> float:
	var amount := Economy.offline_earnings(income_per_sec(), elapsed_sec, offline_cap_sec())
	earn(amount)
	changed.emit()
	return amount


func to_dict() -> Dictionary:
	return {
		"coins": coins,
		"xp": xp,
		"lifetime_coins": lifetime_coins,
		"owned": owned.duplicate(),
		"upgrades": upgrades.duplicate(),
	}


## Loads a dict from to_dict() (possibly JSON round-tripped, so numbers may be floats).
func load_dict(d: Dictionary) -> void:
	_set_defaults()
	coins = float(d.get("coins", coins))
	xp = float(d.get("xp", 0.0))
	lifetime_coins = float(d.get("lifetime_coins", 0.0))
	var saved_owned: Dictionary = d.get("owned", {})
	for id in saved_owned:
		if SpeciesCatalog.by_id(str(id)) != null:
			owned[str(id)] = int(saved_owned[id])
	var saved_upgrades: Dictionary = d.get("upgrades", {})
	for id in upgrades:
		upgrades[id] = int(saved_upgrades.get(id, 0))
	changed.emit()


func _set_defaults() -> void:
	coins = Balance.START_COINS
	xp = 0.0
	lifetime_coins = 0.0
	owned = {}
	upgrades = {Balance.POND_SIZE: 0, Balance.BETTER_FOOD: 0, Balance.DEEP_SLEEP: 0}


## Spending coins earns the same amount of XP.
func _spend(cost: float) -> void:
	var before := level()
	coins -= cost
	xp += cost
	var after := level()
	if after > before:
		leveled_up.emit(after)
