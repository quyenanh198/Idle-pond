extends Control
## Root layout: HUD on top, pond in the middle, tabbed panels at the bottom.

const PondView := preload("res://scripts/pond/pond_view.gd")
const Hud := preload("res://scripts/ui/hud.gd")
const ShopPanel := preload("res://scripts/ui/shop_panel.gd")
const UpgradesPanel := preload("res://scripts/ui/upgrades_panel.gd")
const AccountPanel := preload("res://scripts/ui/account_panel.gd")


func _ready() -> void:
	var t := Theme.new()
	t.default_font_size = 26
	theme = t
	var box := VBoxContainer.new()
	box.set_anchors_preset(PRESET_FULL_RECT)
	box.add_theme_constant_override("separation", 0)
	add_child(box)
	box.add_child(Hud.new())
	var pond := PondView.new()
	pond.size_flags_vertical = SIZE_EXPAND_FILL
	box.add_child(pond)
	var tabs := TabContainer.new()
	tabs.custom_minimum_size.y = 520
	for pair in [["Shop", ShopPanel], ["Upgrades", UpgradesPanel], ["Account", AccountPanel]]:
		var panel: Control = pair[1].new()
		panel.name = pair[0]
		tabs.add_child(panel)
	box.add_child(tabs)
	SaveService.offline_earned.connect(_show_offline)
	SaveService.start()


func _show_offline(amount: float) -> void:
	var d := AcceptDialog.new()
	d.title = "Welcome back!"
	d.dialog_text = "While you were away your fish earned %s coins." % NumberFormat.short(amount)
	add_child(d)
	d.popup_centered()
