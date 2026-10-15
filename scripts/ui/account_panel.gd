extends VBoxContainer
## Guest status, link an email, set password, sign in / out.

var _status: Label
var _email: LineEdit
var _password: LineEdit
var _message: Label
var _buttons: Array[Button] = []


func _ready() -> void:
	_status = Label.new()
	_status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	add_child(_status)
	_email = LineEdit.new()
	_email.placeholder_text = "Email"
	add_child(_email)
	_password = LineEdit.new()
	_password.placeholder_text = "Password (min 6 characters)"
	_password.secret = true
	add_child(_password)
	var grid := GridContainer.new()
	grid.columns = 2
	add_child(grid)
	for pair in [["Link email", _on_link], ["Set password", _on_set_password], ["Sign in", _on_sign_in], ["Sign out", _on_sign_out]]:
		var b := Button.new()
		b.text = pair[0]
		b.size_flags_horizontal = SIZE_EXPAND_FILL
		b.pressed.connect(pair[1])
		grid.add_child(b)
		_buttons.append(b)
	_message = Label.new()
	_message.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	add_child(_message)
	var note := Label.new()
	note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	note.add_theme_font_size_override("font_size", 20)
	note.text = "Signing in keeps whichever pond has earned more coins: this device's or the account's."
	add_child(note)
	visibility_changed.connect(func():
		if is_visible_in_tree():
			_refresh_status())
	_refresh_status()


func _refresh_status() -> void:
	_set_busy(true)
	if not SaveService.client.is_configured():
		_status.text = "Cloud save is not set up (see README). Progress is saved on this device."
		return
	if not await SaveService.client.ensure_session():
		_status.text = "Offline. Progress is saved on this device."
		_set_busy(false)
		return
	var res: Dictionary = await SaveService.client.get_user()
	_set_busy(false)
	if not res.ok or typeof(res.data) != TYPE_DICTIONARY:
		_status.text = "Offline. Progress is saved on this device."
		return
	var user: Dictionary = res.data
	var email := str(user.get("email", ""))
	var pending := str(user.get("new_email", ""))
	if pending != "":
		_status.text = "Confirm %s from your inbox, then set a password." % pending
	elif email == "" or user.get("is_anonymous", false):
		_status.text = "Guest account. Link an email to keep your pond on other devices."
	else:
		_status.text = "Signed in as %s" % email


func _on_link() -> void:
	await _run(SaveService.client.link_email.bind(_email.text.strip_edges()), "Check your inbox to confirm your email.")


func _on_set_password() -> void:
	await _run(SaveService.client.set_password.bind(_password.text), "Password set. You can sign in on other devices.")


func _on_sign_in() -> void:
	await _run(SaveService.sign_in.bind(_email.text.strip_edges(), _password.text), "Signed in.")


func _on_sign_out() -> void:
	_set_busy(true)
	await SaveService.sign_out()
	_message.text = "Signed out. Started a new guest pond."
	await _refresh_status()


## Runs an auth call (a coroutine returning a result dictionary) and shows the outcome.
func _run(action: Callable, success_text: String) -> void:
	_set_busy(true)
	var res: Dictionary = await action.call()
	_message.text = success_text if res.ok else "Error: %s" % res.error
	await _refresh_status()


func _set_busy(busy: bool) -> void:
	for b in _buttons:
		b.disabled = busy
