"""Applies the timeline to the Blender scene, one frame at a time.

For each frame we compute the real-world state (metres) in double precision
and write scene-unit transforms: scene = metres * S, with S = K / view_height.
"""

import math

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

from .. import style
from ..mathutil import clamp, hex_to_linear, lerp, mix_colours, smoothstep
from .models import MOON_DISTANCE, R_EARTH
from .scene import FLAP_SEGMENTS, K

EARTH_MIN_RADIUS = 0.022      # Earth drawn at least this fraction of the view height


def _env_at(alt):
    """Blend the signature environment stops at log10(view height)."""
    stops = style.ENVIRONMENT_STOPS
    if alt <= stops[0][0]:
        a = b = stops[0]
        u = 0.0
    elif alt >= stops[-1][0]:
        a = b = stops[-1]
        u = 0.0
    else:
        for a, b in zip(stops, stops[1:]):
            if a[0] <= alt <= b[0]:
                break
        u = smoothstep(a[0], b[0], alt)
    col = lambda i: mix_colours(hex_to_linear(a[i]), hex_to_linear(b[i]), u)
    num = lambda i: lerp(a[i], b[i], u)
    return dict(zenith=col(1), horizon=col(2), ground=col(3), grid=num(4), stars=num(5), sun=num(6))


class Animator:
    def __init__(self, refs, timeline, cfg):
        self.refs = refs
        self.tl = timeline
        self.cfg = cfg
        self.scene = bpy.context.scene
        self.t0 = cfg["thickness_mm"] / 1000.0
        # The Moon sits just left of the column at the finale framing.
        n = timeline.N
        v_fin = timeline._view_landmark(n) if n in timeline.beats else timeline._view_stack(n)
        x_target = -(style.COLUMN_MIN_WIDTH / 2 + 0.014 + 0.035) * v_fin
        self.moon_angle = math.asin(clamp(x_target / MOON_DISTANCE, -0.9, 0.9))

    # --- helpers -------------------------------------------------------------

    def _set_value(self, node_map, name, value):
        node_map[name].outputs[0].default_value = value

    def _set_colour(self, node, colour):
        node.outputs[0].default_value = tuple(colour[:3]) + (1.0,)

    # --- main entry ----------------------------------------------------------

    def apply(self, t):
        tl, refs = self.tl, self.refs
        V = tl.view_height(t)
        S = K / V
        self.S, self.V = S, V
        self._camera(t)
        r_disp = max(R_EARTH, EARTH_MIN_RADIUS * V)
        self.earth_centre = (0.0, 0.0, -r_disp)
        self._environment(t, V, S, r_disp)
        stack_h = self._stack(t, V, S)
        boosted = self._landmarks(t, V, S, r_disp)
        bpy.context.view_layer.update()
        return self._record(t, V, stack_h, boosted)

    # --- camera ----------------------------------------------------------------

    def _camera(self, t):
        tl, refs = self.tl, self.refs
        e = math.radians(tl.elevation(t))
        a = math.radians(tl.azimuth(t))
        d = refs.camera_distance
        pos = Vector((d * math.sin(a) * math.cos(e), -d * math.cos(a) * math.cos(e), d * math.sin(e)))
        cam = refs.camera
        cam.location = pos
        cam.rotation_euler = (-pos).to_track_quat("-Z", "Y").to_euler()
        # Lens shift puts the foot of the stack where the layout wants it.
        w, h = refs.width, refs.height
        sy = lerp(style.SUBJECT_Y_FOLDING, style.SUBJECT_Y_COLUMN, tl.column_blend(t))
        sy = lerp(sy, style.SUBJECT_Y_SPACE, smoothstep(5.6, 7.4, math.log10(tl.view_height(t))))
        cam.data.shift_x = (0.5 - style.SUBJECT_X) * w / max(w, h)
        cam.data.shift_y = (sy - 0.5) * h / max(w, h)

        # Key light from the camera's upper left; it travels along -Z of the lamp.
        sa = a + math.radians(style.SUN_AZIMUTH_OFFSET_DEG)
        se = math.radians(lerp(style.SUN_ELEVATION_FOLDING_DEG, style.SUN_ELEVATION_COLUMN_DEG,
                               tl.column_blend(t)))
        to_sun = Vector((math.sin(sa) * math.cos(se), -math.cos(sa) * math.cos(se), math.sin(se)))
        refs.sun_obj.rotation_euler = (-to_sun).to_track_quat("-Z", "Y").to_euler()

    # --- environment ----------------------------------------------------------

    def _environment(self, t, V, S, r_disp):
        refs = self.refs
        alt = math.log10(V)
        env = _env_at(alt)
        self._set_colour(refs.world_zenith, env["zenith"])
        self._set_colour(refs.world_horizon, env["horizon"])
        sky_avg = mix_colours(env["zenith"], env["horizon"], 0.5)
        day = 1.0 - smoothstep(4.5, 6.2, alt)
        ambient = tuple(c * lerp(0.0, 0.42, day) + 0.03 for c in sky_avg)
        self._set_colour(refs.world_ambient, ambient)
        refs.world_stars.outputs[0].default_value = env["stars"]
        refs.sun.energy = env["sun"]
        refs.fill.energy = lerp(0.22, 0.10, day)

        on_ground = V < style.EARTH_SWITCH_M
        refs.ground.hide_render = not on_ground
        for obj in (refs.earth,):
            obj.hide_render = on_ground
        if on_ground:
            g = refs.ground_nodes
            self._set_colour(g["ground"], env["ground"])
            self._set_colour(g["horizon"], env["horizon"])
            # Two grid levels a decade apart; each fades with its density so
            # the grid "zooms" seamlessly through powers of ten.
            s_major = 10 ** math.ceil(math.log10(V / 10.0))
            for key, spacing in (("1", s_major / 10.0), ("2", s_major)):
                density = V / spacing
                g["grid_s" + key].outputs[0].default_value = spacing * S
                g["grid_a" + key].outputs[0].default_value = 1.0 - smoothstep(25.0, 90.0, density)
                g["grid_w" + key].outputs[0].default_value = lerp(0.010, 0.024, smoothstep(30.0, 3.0, density))
            g["grid_strength"].outputs[0].default_value = env["grid"] * 0.45
        else:
            earth = refs.earth
            earth.location = (0.0, 0.0, -r_disp * S)
            earth.scale = (r_disp * S,) * 3
        clouds = smoothstep(5.3, 6.3, alt) * 0.8
        atmo = smoothstep(6.1, 6.7, alt)
        for obj, amount, node in ((refs.clouds, clouds, refs.cloud_opacity),
                                  (refs.atmosphere, atmo, refs.atmo_strength)):
            obj.hide_render = on_ground or amount <= 0.001
            node.outputs[0].default_value = amount
            obj.location = (0.0, 0.0, -r_disp * S)
            obj.scale = (r_disp * S,) * 3

    # --- the stack ------------------------------------------------------------

    def _stack(self, t, V, S):
        tl, refs = self.tl, self.refs
        st = tl.stack_state(t)
        stack, flap = refs.stack, refs.flap
        px_per_unit = refs.height / K
        layer_px = self.t0 * S * px_per_unit
        nodes = refs.stack_nodes
        self._set_value(nodes, "layer_px", layer_px)
        self._set_value(nodes, "layer_strength", smoothstep(2.0, 5.0, layer_px) * 0.9)
        self._set_value(nodes, "band_strength", 1.0)
        self._set_value(nodes, "flash", self._flash(t))

        if st["phase"] == "folding":
            self._folding(st, S)
            return st["h"] * 2

        flap.hide_render = True
        lx, ly, h = st["lx"], st["ly"], st["h"]
        if st["phase"] == "column":
            # Never thinner than a readable fraction of the view.
            frac = lerp(style.COLUMN_MIN_WIDTH, style.COLUMN_MIN_WIDTH_SPACE,
                        smoothstep(6.3, 8.6, math.log10(V)))
            widen = max(1.0, frac * V / max(lx, ly))
            lx, ly = lx * widen, ly * widen
        sq = st["squash"]
        stack.location = (0.0, 0.0, 0.0)
        stack.rotation_euler = (0.0, 0.0, 0.0)
        stack.scale = (lx * S * (1 + sq * 0.5), ly * S * (1 + sq * 0.5), max(h * S * (1 - sq), 1e-5))
        self._box_uv(stack, refs.stack_loops, 0.0, h / self.t0)
        return h

    def _flash(self, t):
        """Brief glow on the stack when a fold lands."""
        for f in self.tl.folds:
            dt = t - f.t_land
            if 0 <= dt < 0.4:
                peak = 0.10 if f.mode == "physical" else 0.22
                return peak * (1 - smoothstep(0.0, 0.4, dt))
        return 0.0

    def _box_uv(self, obj, loops, u_bottom, u_top):
        uv = []
        for vi in loops:
            uv += [u_bottom if vi < 4 else u_top, 0.0]
        obj.data.uv_layers["Layers"].data.foreach_set("uv", uv)

    def _folding(self, st, S):
        """Half the stack stays put; the other half (the flap) bends over onto it."""
        refs = self.refs
        stack, flap = refs.stack, refs.flap
        lx, ly, T = st["lx"], st["ly"], st["h"]
        if st["axis"] == "x":
            L, W, rot = lx, ly, 0.0
        else:
            L, W, rot = ly, lx, math.pi / 2
        H = L / 2
        offset = H / 2 * st["slide"]           # recentre the result as it folds
        cr, sr = math.cos(rot), math.sin(rot)

        # Stationary half: u in [-L/2, 0].
        uc = -H / 2 + offset
        stack.rotation_euler = (0.0, 0.0, rot)
        stack.location = (uc * cr * S, uc * sr * S, 0.0)
        stack.scale = (H * S, W * S, T * S)
        layers_prev = T / self.t0
        self._box_uv(stack, refs.stack_loops, 0.0, layers_prev)

        # Flap: hinge at the top edge of the fold line. The far end lags a
        # little while thin sheets flip, so it curls like real paper.
        theta = st["theta"]
        curl = 0.9 * max(0.0, 1.0 - T / (0.08 * H)) * math.sin(theta)
        kappa = -curl / H
        coords, uvs = [], []
        for i in range(FLAP_SEGMENTS + 1):
            s = H * i / FLAP_SEGMENTS
            a = theta + kappa * s
            if abs(kappa) > 1e-9:
                px = (math.sin(a) - math.sin(theta)) / kappa
                pz = (math.cos(theta) - math.cos(a)) / kappa
            else:
                px, pz = s * math.cos(theta), s * math.sin(theta)
            nx, nz = math.sin(a), -math.cos(a)
            for j in (0, 1):
                w = (j - 0.5) * W
                for k in (0, 1):
                    d = T * (1 - k)
                    u = offset + px + d * nx
                    z = T + pz + d * nz
                    coords += [u * S, w * S, z * S]
        flap.data.vertices.foreach_set("co", coords)
        flap.data.update()
        for vi in refs.flap_loops:
            k = vi % 2
            uvs += [layers_prev * (2 - k), 0.0]
        flap.data.uv_layers["Layers"].data.foreach_set("uv", uvs)
        flap.rotation_euler = (0.0, 0.0, rot)
        flap.location = (0.0, 0.0, 0.0)
        flap.hide_render = False

    # --- landmarks ------------------------------------------------------------

    def _landmarks(self, t, V, S, r_disp):
        tl = self.tl
        ec = self.earth_centre
        boosted = False
        self.anchor_world = {}
        for lm in self.refs.landmarks:
            pres = tl.landmark_presence(lm.window, t)
            visible = pres > 1e-3
            for g in lm.groups.values():
                for obj in g.objects:
                    obj.hide_render = not visible
                for ring, _ in g.rings:
                    ring.hide_render = not visible
                if not visible:
                    continue
                boost = max(1.0, g.boost_min * V / g.size_m) if g.boost_min else 1.0
                boosted = boosted or boost > 1.05
                if g.name == "moon":
                    a = self.moon_angle
                    pos = (ec[0] + MOON_DISTANCE * math.sin(a), 0.0, ec[2] + MOON_DISTANCE * math.cos(a))
                else:
                    x, y, z = g.pos
                    drop = (x * x + y * y) / (2 * r_disp)  # sit on the curved Earth
                    pos = (x, y, z - drop)
                root = g.root
                root.location = tuple(c * S for c in pos)
                root.scale = (S * boost * pres,) * 3
                rz = g.rotation_z
                if getattr(g, "face_camera", False):
                    rz += math.radians(tl.azimuth(t))
                root.rotation_euler = (0.0, 0.0, rz)
                for ring, radius in g.rings:
                    ring.location = tuple(c * S for c in ec)
                    ring.scale = (radius * S,) * 3
                    ring.data.bevel_depth = 0.018 / (radius * S)
                    ring.active_material.node_tree.nodes[ring["ring_alpha_node"]].inputs[0].default_value = 0.3 * pres
                for key, local in g.anchors.items():
                    self.anchor_world[(lm.id, key)] = (root, Vector(local), pres)
        return boosted

    # --- per-frame record for the overlay / audio -----------------------------

    def _project(self, world):
        cam = self.refs.camera
        co = world_to_camera_view(self.scene, cam, world)
        return [round(co.x * style.WIDTH, 1), round((1 - co.y) * style.HEIGHT, 1), co.z > 0]

    def _record(self, t, V, stack_h, boosted):
        anchors = {}
        for (lm_id, key), (root, local, pres) in self.anchor_world.items():
            x, y, ok = self._project(root.matrix_world @ local)
            anchors.setdefault(lm_id, {})[key] = [x, y, round(pres, 3), ok]
        sx, sy, _ = self._project(Vector((0.0, 0.0, stack_h * self.S)))
        bx, by, _ = self._project(Vector((0.0, 0.0, 0.0)))
        return dict(t=round(t, 4), view_m=V, stack_m=stack_h, count=self.tl.count_at(t),
                    stack_top=[sx, sy], stack_base=[bx, by], anchors=anchors, boosted=boosted)
