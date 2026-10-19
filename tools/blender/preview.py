"""Shared preview renders for the model scripts: a studio close-up setup and a pond scene."""
import math

import bpy
from mathutils import Vector


class Previewer:
    """Cycles camera, studio lights and a pond scene for checking a model."""

    def __init__(self, out_dir, prefix):
        self.out_dir, self.prefix = out_dir, prefix
        self.scene = scene = bpy.context.scene
        scene.render.engine = "CYCLES"
        scene.cycles.device = "CPU"
        scene.cycles.samples = 128
        scene.cycles.use_denoising = True
        scene.render.resolution_x, scene.render.resolution_y = 1280, 800
        scene.view_settings.view_transform = "AgX"
        scene.view_settings.look = "AgX - Medium High Contrast"
        self.target = bpy.data.objects.new("Target", None)
        scene.collection.objects.link(self.target)
        self.cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
        scene.collection.objects.link(self.cam)
        scene.camera = self.cam
        self._track(self.cam)
        self.cam.data.dof.use_dof = True
        self.cam.data.dof.aperture_fstop = 5.6
        self.studio = [
            self._area("Key", (2.2, -2.6, 3.0), 650, 3.0, (1.0, 0.97, 0.92)),
            self._area("Rim", (-2.8, 2.4, 1.6), 450, 2.0, (0.85, 0.92, 1.0)),
            self._area("Fill", (0.5, -4.0, 0.0), 90, 4.0, (1.0, 1.0, 1.0)),
        ]
        scene.world = bpy.data.worlds.new("W")
        self.bg = scene.world.node_tree.nodes["Background"]
        self.bg.inputs["Color"].default_value = (0.008, 0.022, 0.026, 1)

    def _track(self, ob):
        c = ob.constraints.new("TRACK_TO")
        c.target = self.target
        c.track_axis = "TRACK_NEGATIVE_Z"
        c.up_axis = "UP_Y"

    def _area(self, name, loc, energy, size, color):
        light = bpy.data.objects.new(name, bpy.data.lights.new(name, "AREA"))
        self.scene.collection.objects.link(light)
        light.data.energy, light.data.size, light.data.color = energy, size, color
        light.location = loc
        self._track(light)
        return light

    def render(self, name, frame, cam_loc, tgt, lens, focus):
        self.scene.frame_set(frame)
        self.cam.location = cam_loc
        self.target.location = tgt
        self.cam.data.lens = lens
        self.cam.data.dof.focus_distance = (Vector(cam_loc) - Vector(focus)).length
        self.scene.render.filepath = f"{self.out_dir}/{self.prefix}_{name}.png"
        bpy.ops.render.render(write_still=True)

    def pond(self, surface_z=0.34, floor_z=-0.9):
        """Switches to the pond scene: gravel floor, green-tinted water, rippled surface, sun and sky."""
        for light in self.studio:
            light.hide_render = True
        bpy.ops.mesh.primitive_plane_add(size=14, location=(0, 0, floor_z))
        floor = bpy.context.active_object
        m = bpy.data.materials.new("Gravel")
        nt = m.node_tree
        b = nt.nodes["Principled BSDF"]
        edge = nt.nodes.new("ShaderNodeTexVoronoi")
        edge.feature = "DISTANCE_TO_EDGE"
        edge.inputs["Scale"].default_value = 260
        cell = nt.nodes.new("ShaderNodeTexVoronoi")
        cell.inputs["Scale"].default_value = 260
        rounded = nt.nodes.new("ShaderNodeMapRange")
        rounded.inputs["From Max"].default_value = 0.45
        rounded.interpolation_type = "SMOOTHSTEP"
        nt.links.new(edge.outputs["Distance"], rounded.inputs["Value"])
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (0.05, 0.047, 0.04, 1)
        ramp.color_ramp.elements[1].color = (0.33, 0.30, 0.24, 1)
        nt.links.new(cell.outputs["Color"], ramp.inputs["Fac"])
        gmix = nt.nodes.new("ShaderNodeMix")
        gmix.data_type = "RGBA"
        gmix.inputs["A"].default_value = (0.045, 0.04, 0.03, 1)
        nt.links.new(rounded.outputs["Result"], gmix.inputs["Factor"])
        nt.links.new(ramp.outputs["Color"], gmix.inputs["B"])
        nt.links.new(gmix.outputs["Result"], b.inputs["Base Color"])
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Distance"].default_value = 0.008
        nt.links.new(rounded.outputs["Result"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
        b.inputs["Roughness"].default_value = 0.6
        floor.data.materials.append(m)

        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, (surface_z - 0.01 + floor_z - 0.02) / 2))
        water = bpy.context.active_object
        water.scale = (14, 14, surface_z - 0.01 - floor_z + 0.02)
        m = bpy.data.materials.new("WaterVolume")
        nt = m.node_tree
        nt.nodes.remove(nt.nodes["Principled BSDF"])
        vol = nt.nodes.new("ShaderNodeVolumeAbsorption")
        vol.inputs["Color"].default_value = (0.42, 0.70, 0.56, 1)
        vol.inputs["Density"].default_value = 0.5
        nt.links.new(vol.outputs["Volume"], nt.nodes["Material Output"].inputs["Volume"])
        water.data.materials.append(m)

        bpy.ops.mesh.primitive_plane_add(size=14, location=(0, 0, surface_z))
        surface = bpy.context.active_object
        m = bpy.data.materials.new("WaterSurface")
        nt = m.node_tree
        nt.nodes.remove(nt.nodes["Principled BSDF"])
        glass = nt.nodes.new("ShaderNodeBsdfGlass")
        glass.inputs["IOR"].default_value = 1.333
        glass.inputs["Roughness"].default_value = 0.0
        noise = nt.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 2.5
        noise.inputs["Detail"].default_value = 4
        wb = nt.nodes.new("ShaderNodeBump")
        wb.inputs["Strength"].default_value = 0.12
        nt.links.new(noise.outputs["Fac"], wb.inputs["Height"])
        nt.links.new(wb.outputs["Normal"], glass.inputs["Normal"])
        nt.links.new(glass.outputs["BSDF"], nt.nodes["Material Output"].inputs["Surface"])
        surface.data.materials.append(m)
        surface.visible_shadow = False   # let sunlight reach underwater objects

        sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
        self.scene.collection.objects.link(sun)
        sun.rotation_euler = (math.radians(32), math.radians(-12), math.radians(25))
        sun.data.energy = 4.0
        sun.data.angle = math.radians(2)
        self.bg.inputs["Color"].default_value = (0.55, 0.68, 0.85, 1)
        self.scene.cycles.samples = 96
        self.cam.data.dof.aperture_fstop = 11
