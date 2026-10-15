shader_type canvas_item;
// Side-view water: depth gradient, drifting light rays, wavy surface line.

uniform vec4 surface_color : source_color = vec4(0.36, 0.78, 0.92, 1.0);
uniform vec4 deep_color : source_color = vec4(0.03, 0.18, 0.36, 1.0);
uniform vec4 sky_color : source_color = vec4(0.85, 0.95, 1.0, 1.0);
uniform float ray_strength = 0.12;

void fragment() {
	vec2 uv = UV;
	vec3 col = mix(surface_color.rgb, deep_color.rgb, smoothstep(0.0, 1.0, uv.y));
	float rays = sin(uv.x * 18.0 + uv.y * 6.0 + TIME * 0.6) * sin(uv.x * 7.0 - TIME * 0.35);
	col += ray_strength * max(rays, 0.0) * (1.0 - uv.y);
	float wave = 0.03 + 0.008 * sin(uv.x * 20.0 + TIME * 2.0);
	col = mix(sky_color.rgb, col, smoothstep(wave - 0.004, wave + 0.004, uv.y));
	COLOR = vec4(col, 1.0);
}
