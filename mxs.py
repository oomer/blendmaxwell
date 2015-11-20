# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import os
import platform
import datetime
import struct
import math
import sys

from .log import log, LogStyles
from . import utils

s = platform.system()
if(s == 'Darwin'):
    pass
elif(s == 'Linux'):
    try:
        from pymaxwell import *
    except ImportError:
        mp = os.environ.get("MAXWELL3_ROOT")
        sys.path.append(os.path.abspath(os.path.join(mp, 'python', 'pymaxwell', 'python3.4')))
        from pymaxwell import *
elif(s == 'Windows'):
    try:
        from pymaxwell import *
    except ImportError:
        mp = os.environ.get("MAXWELL3_ROOT")
        sys.path.append(os.path.abspath(os.path.join(mp, 'python', 'pymaxwell', 'python3.4')))
        os.environ['PATH'] = ';'.join([mp, os.environ['PATH']])
        from pymaxwell import *


def read_mxm_preview(path):
    import numpy
    s = Cmaxwell(mwcallback)
    m = s.readMaterial(path)
    a = m.getPreview()[0]
    r = numpy.copy(a)
    return r


class MXSWriter():
    def __init__(self, path, append=False, ):
        """Create scene or load existing.
        path    string (path)
        append  bool
        """
        
        if(__name__ != "__main__"):
            if(platform.system() == 'Darwin'):
                raise ImportError("No pymaxwell directly in Blender on Mac OS X..")
        
        log(self.__class__.__name__, 1, LogStyles.MESSAGE, prefix="* ", )
        
        self.path = path
        self.mxs = Cmaxwell(mwcallback)
        
        pid = utils.get_plugin_id()
        if(pid != ""):
            # write here directly, even though it is also part of scene data, but api change just for this is pointless..
            self.mxs.setPluginID(pid)
        
        if(append):
            log("appending to existing scene..", 2, prefix="* ", )
            self.mxs.readMXS(self.path)
        else:
            log("creating new scene..", 2, prefix="* ", )
        
        self.mgr = CextensionManager.instance()
        self.mgr.loadAllExtensions()
        
        # self.matdb = []
    
    def write(self):
        """Write scene fo file.
        (no parameters..)
        """
        log("saving scene..", 2)
        ok = self.mxs.writeMXS(self.path)
        log("done.", 2)
        return ok
    
    def erase_unused_materials(self):
        self.mxs.eraseUnusedMaterials()
    
    def set_base_and_pivot(self, o, matrix=None, ):
        """Convert float tuples to Cbases and set to object.
        o       CmaxwellObject
        base    ((3 float), (3 float), (3 float), (3 float)) or None
        pivot   ((3 float), (3 float), (3 float), (3 float)) or None
        """
        if(matrix is None):
            matrix = ([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
                      [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
                      [0.0, 0.0, 0.0],
                      [0.0, 0.0, 0.0],
                      [0.0, 0.0, 0.0])
        base = matrix[0]
        pivot = matrix[1]
        l = matrix[2]
        r = matrix[3]
        s = matrix[4]
        
        b = Cbase()
        b.origin = Cvector(*base[0])
        b.xAxis = Cvector(*base[1])
        b.yAxis = Cvector(*base[2])
        b.zAxis = Cvector(*base[3])
        p = Cbase()
        p.origin = Cvector(*pivot[0])
        p.xAxis = Cvector(*pivot[1])
        p.yAxis = Cvector(*pivot[2])
        p.zAxis = Cvector(*pivot[3])
        o.setBaseAndPivot(b, p)
        
        o.setPivotPosition(Cvector(*l))
        o.setPivotRotation(Cvector(*r))
        o.setPosition(Cvector(*l))
        o.setRotation(Cvector(*r))
        o.setScale(Cvector(*s))
    
    def set_object_props(self, o, hide=False, opacity=100, cid=(255, 255, 255), hcam=False, hcamsc=False, hgi=False, hrr=False, hzcp=False, blocked_emitters=None, ):
        """Set common object properties.
        o                   CmaxwellObject
        hide                bool
        opacity             float
        cid                 (int, int, int) 0-255 rgb
        hcam                bool
        hcamsc              bool
        hgi                 bool
        hrr                 bool
        hzcp                bool
        blocked_emitters    list of blocked emitter object names
        """
        if(hide):
            o.setHide(hide)
        if(opacity != 100.0):
            o.setOpacity(opacity)
        c = Crgb()
        c.assign(*[v / 255 for v in cid])
        o.setColorID(c)
        if(hcam):
            o.setHideToCamera(True)
        if(hcamsc):
            o.setHideToCameraInShadowsPass(True)
        if(hgi):
            o.setHideToGI(True)
        if(hrr):
            o.setHideToReflectionsRefractions(True)
        if(hzcp):
            o.excludeOfCutPlanes(True)
        if(blocked_emitters):
            for n in blocked_emitters:
                ok = o.addExcludedLight(n)
    
    def texture_data_to_mxparams(self, name, data, mxparams, ):
        """Create CtextureMap, fill with parameters and put into mxparams.
        name        string
        data        dict {'type':               string,
                          'path':               string,
                          'channel':            int,
                          'use_override_map':   bool,
                          'tile_method_type':   [bool, bool],
                          'tile_method_units':  int,
                          'repeat':             [float, float],
                          'mirror':             [bool, bool],
                          'offset':             [float, float],
                          'rotation':           float,
                          'invert':             bool,
                          'alpha_only':         bool,
                          'interpolation':      bool,
                          'brightness':         float,
                          'contrast':           float,
                          'saturation':         float,
                          'hue':                float,
                          'rgb_clamp':          [float, float], }
        mxparams    mxparams
        """
        d = data
        if(d is None):
            return
        
        # t = mxparams.getTextureMap(name)[0]
        t = CtextureMap()
        t.setPath(d['path'])
        v = Cvector2D()
        v.assign(*d['repeat'])
        t.scale = v
        v = Cvector2D()
        v.assign(*d['offset'])
        t.offset = v
        t.rotation = d['rotation']
        t.uvwChannelID = d['channel']
        t.uIsTiled = d['tile_method_type'][0]
        t.vIsTiled = d['tile_method_type'][1]
        t.uIsMirrored = d['mirror'][0]
        t.vIsMirrored = d['mirror'][1]
        t.invert = d['invert']
        # t.doGammaCorrection = 0
        t.useAbsoluteUnits = d['tile_method_units']
        # t.normalMappingFlipRed = 0
        # t.normalMappingFlipGreen = 0
        # t.normalMappingFullRangeBlue = 0
        t.useAlpha = d['alpha_only']
        t.typeInterpolation = d['interpolation']
        t.saturation = d['saturation'] / 100
        t.contrast = d['contrast'] / 100
        t.brightness = d['brightness'] / 100
        t.hue = d['hue'] / 180
        t.clampMin = d['rgb_clamp'][0] / 255
        t.clampMax = d['rgb_clamp'][1] / 255
        t.useGlobalMap = d['use_override_map']
        # t.cosA = 1.000000
        # t.sinA = 0.000000
        ok = mxparams.setTextureMap(name, t)
        return mxparams
    
    def texture(self, d, ):
        """Create CtextureMap from parameters
        d   dict
        """
        if(d is None):
            return
        
        s = self.mxs
        
        t = CtextureMap()
        t.setPath(d['path'])
        
        t.uvwChannelID = d['channel']
        
        t.brightness = d['brightness'] / 100
        t.contrast = d['contrast'] / 100
        t.saturation = d['saturation'] / 100
        t.hue = d['hue'] / 180
        
        t.useGlobalMap = d['use_override_map']
        t.useAbsoluteUnits = d['tile_method_units']
        
        t.uIsTiled = d['tile_method_type'][0]
        t.vIsTiled = d['tile_method_type'][1]
        
        t.uIsMirrored = d['mirror'][0]
        t.vIsMirrored = d['mirror'][1]
        
        vec = Cvector2D()
        vec.assign(d['offset'][0], d['offset'][1])
        t.offset = vec
        t.rotation = d['rotation']
        t.invert = d['invert']
        t.useAlpha = d['alpha_only']
        if(d['interpolation']):
            t.typeInterpolation = 1
        else:
            t.typeInterpolation = 0
        t.clampMin = d['rgb_clamp'][0] / 255
        t.clampMax = d['rgb_clamp'][1] / 255
        
        vec = Cvector2D()
        vec.assign(d['repeat'][0], d['repeat'][1])
        t.scale = vec
        
        return t
    
    def material_placeholder(self, n=None, ):
        if(n is not None):
            # n = '{}_{}'.format(n, 'MATERIAL_PLACEHOLDER')
            pass
        else:
            n = 'MATERIAL_PLACEHOLDER'
        
        s = self.mxs
        m = s.createMaterial(n)
        l = m.addLayer()
        b = l.addBSDF()
        r = b.getReflectance()
        a = Cattribute()
        a.activeType = MAP_TYPE_BITMAP
        t = CtextureMap()
        mgr = CextensionManager.instance()
        mgr.loadAllExtensions()
        e = mgr.createDefaultTextureExtension('Checker')
        ch = e.getExtensionData()
        ch.setUInt('Number of elements U', 32)
        ch.setUInt('Number of elements V', 32)
        t.addProceduralTexture(ch)
        a.textureMap = t
        r.setAttribute('color', a)
        return m
    
    def material_default(self, n, ):
        s = self.mxs
        m = s.createMaterial(n)
        l = m.addLayer()
        b = l.addBSDF()
        return m
    
    def material_external(self, d, ):
        s = self.mxs
        p = d['path']
        t = s.readMaterial(p)
        t.setName(d['name'])
        m = s.addMaterial(t)
        if(not d['embed']):
            m.setReference(1, p)
        return m
    
    def material_custom(self, d, ):
        s = self.mxs
        
        m = s.createMaterial(d['name'])
        d = d['data']
        
        def global_props(d, m):
            # global properties
            if(d['override_map']):
                t = texture(d['override_map'], s, )
                if(t is not None):
                    m.setGlobalMap(t)
            
            if(d['bump']):
                a = Cattribute()
                a.activeType = MAP_TYPE_BITMAP
                t = texture(d['bump_map'], s, )
                if(t is not None):
                    a.textureMap = t
                a.value = d['bump_value']
                m.setAttribute('bump', a)
            
            m.setDispersion(d['dispersion'])
            m.setMatteShadow(d['shadow'])
            m.setMatte(d['matte'])
            m.setNestedPriority(d['priority'])
            
            c = Crgb()
            cc = [c / 255 for c in d['id']]
            c.assign(*cc)
            m.setColorID(c)
            
            if(d['active_display_map']):
                t = texture(d['active_display_map'], s, )
                m.setActiveDisplayMap(t)
        
        def displacement(d, m):
            if(not d['enabled']):
                return
            
            m.enableDisplacement(True)
            if(d['map'] is not None):
                t = texture(d['map'], s)
                m.setDisplacementMap(t)
            m.setDisplacementCommonParameters(d['type'], d['subdivision'], int(d['smoothing']), d['offset'], d['subdivision_method'], d['uv_interpolation'], )
            m.setHeightMapDisplacementParameters(d['height'], d['height_units'], d['adaptive'], )
            v = Cvector(*d['v3d_scale'])
            m.setVectorDisplacementParameters(v, d['v3d_transform'], d['v3d_rgb_mapping'], d['v3d_preset'], )
        
        def add_bsdf(d, l):
            b = l.addBSDF()
            b.setName(d['name'])
            
            bp = d['bsdf_props']
            # weight
            if(bp['weight_map_enabled']):
                # t = texture(bp['weight_map'], s, )
                # a = Cattribute()
                # a.textureMap = t
                a = Cattribute()
                a.activeType = MAP_TYPE_BITMAP
                t = texture(bp['weight_map'], s, )
                if(t is not None):
                    a.textureMap = t
                a.value = bp['weight']
            else:
                a = Cattribute()
                a.activeType = MAP_TYPE_VALUE
                a.value = bp['weight']
            b.setWeight(a)
            # enabled
            if(not bp['visible']):
                b.setState(False)
            # ior
            r = b.getReflectance()
            if(bp['ior'] == 1):
                # measured data
                r.setActiveIorMode(1)
                r.setComplexIor(bp['complex_ior'])
            else:
                if(bp['reflectance_0_map_enabled']):
                    # t = texture(bp['reflectance_0_map'], s, )
                    # a = Cattribute()
                    # a.textureMap = t
                    a = Cattribute()
                    a.activeType = MAP_TYPE_BITMAP
                    t = texture(bp['reflectance_0_map'], s, )
                    if(t is not None):
                        a.textureMap = t
                    # a.value = bp['weight']
                    a.rgb.assign(*bp['reflectance_0'])
                else:
                    a = Cattribute()
                    a.activeType = MAP_TYPE_RGB
                    a.rgb.assign(*bp['reflectance_0'])
                r.setAttribute('color', a)
                
                if(bp['reflectance_90_map_enabled']):
                    # # a = texture(bp['reflectance_90_map'], s, )
                    # t = texture(bp['reflectance_90_map'], s, )
                    # a = Cattribute()
                    # a.textureMap = t
                    a = Cattribute()
                    a.activeType = MAP_TYPE_BITMAP
                    t = texture(bp['reflectance_90_map'], s, )
                    if(t is not None):
                        a.textureMap = t
                    # a.value = bp['weight']
                    a.rgb.assign(*bp['reflectance_90'])
                else:
                    a = Cattribute()
                    a.activeType = MAP_TYPE_RGB
                    a.rgb.assign(*bp['reflectance_90'])
                r.setAttribute('color.tangential', a)
                
                if(bp['transmittance_map_enabled']):
                    # # a = texture(bp['transmittance_map'], s, )
                    # t = texture(bp['transmittance_map'], s, )
                    # a = Cattribute()
                    # a.textureMap = t
                    a = Cattribute()
                    a.activeType = MAP_TYPE_BITMAP
                    t = texture(bp['transmittance_map'], s, )
                    if(t is not None):
                        a.textureMap = t
                    # a.value = bp['weight']
                    a.rgb.assign(*bp['transmittance'])
                else:
                    a = Cattribute()
                    a.activeType = MAP_TYPE_RGB
                    a.rgb.assign(*bp['transmittance'])
                r.setAttribute('transmittance.color', a)
                
                r.setAbsorptionDistance(bp['attenuation_units'], bp['attenuation'])
                r.setIOR(bp['nd'], bp['abbe'])
                if(bp['force_fresnel']):
                    r.enableForceFresnel(True)
                r.setConductor(bp['k'])
                if(bp['r2_enabled']):
                    r.setFresnelCustom(bp['r2_falloff_angle'], bp['r2_influence'], True, )
            # surface
            if(bp['roughness_map_enabled']):
                # # a = texture(bp['roughness_map'], s, )
                # t = texture(bp['roughness_map'], s, )
                # a = Cattribute()
                # a.textureMap = t
                a = Cattribute()
                a.activeType = MAP_TYPE_BITMAP
                t = texture(bp['roughness_map'], s, )
                if(t is not None):
                    a.textureMap = t
                a.value = bp['roughness']
                # a.rgb.assign(*bp['transmittance'])
            else:
                a = Cattribute()
                a.activeType = MAP_TYPE_VALUE
                a.value = bp['roughness']
            b.setAttribute('roughness', a)
            
            if(bp['bump_map_enabled']):
                # # a = texture(bp['bump_map'], s, )
                # t = texture(bp['bump_map'], s, )
                # a = Cattribute()
                # a.textureMap = t
                a = Cattribute()
                a.activeType = MAP_TYPE_BITMAP
                t = texture(bp['bump_map'], s, )
                if(t is not None):
                    a.textureMap = t
                a.value = bp['bump']
                # a.rgb.assign(*bp['transmittance'])
            else:
                a = Cattribute()
                a.activeType = MAP_TYPE_VALUE
                a.value = bp['bump']
            b.setAttribute('bump', a)
            b.setNormalMapState(bp['bump_map_use_normal'])
            
            if(bp['anisotrophy_map_enabled']):
                # # a = texture(bp['anisotrophy_map'], s, )
                # t = texture(bp['anisotrophy_map'], s, )
                # a = Cattribute()
                # a.textureMap = t
                a = Cattribute()
                a.activeType = MAP_TYPE_BITMAP
                t = texture(bp['anisotrophy_map'], s, )
                if(t is not None):
                    a.textureMap = t
                a.value = bp['anisotrophy']
                # a.rgb.assign(*bp['transmittance'])
            else:
                a = Cattribute()
                a.activeType = MAP_TYPE_VALUE
                a.value = bp['anisotrophy']
            b.setAttribute('anisotrophy', a)
            
            if(bp['anisotrophy_angle_map_enabled']):
                # # a = texture(bp['anisotrophy_angle_map'], s, )
                # t = texture(bp['anisotrophy_angle_map'], s, )
                # a = Cattribute()
                # a.textureMap = t
                a = Cattribute()
                a.activeType = MAP_TYPE_BITMAP
                t = texture(bp['anisotrophy_angle_map'], s, )
                if(t is not None):
                    a.textureMap = t
                a.value = bp['anisotrophy_angle']
                # a.rgb.assign(*bp['transmittance'])
            else:
                a = Cattribute()
                a.activeType = MAP_TYPE_VALUE
                a.value = bp['anisotrophy_angle']
            b.setAttribute('angle', a)
            
            # subsurface
            a = Cattribute()
            a.activeType = MAP_TYPE_RGB
            a.rgb.assign(*bp['scattering'])
            r.setAttribute('scattering', a)
            r.setScatteringParameters(bp['coef'], bp['asymmetry'], bp['single_sided'])
            if(bp['single_sided']):
                if(bp['single_sided_map_enabled']):
                    # # a = texture(bp['single_sided_map'], s, )
                    # t = texture(bp['single_sided_map'], s, )
                    # a = Cattribute()
                    # a.textureMap = t
                    a = Cattribute()
                    a.activeType = MAP_TYPE_BITMAP
                    t = texture(bp['single_sided_map'], s, )
                    if(t is not None):
                        a.textureMap = t
                    a.value = bp['single_sided_value']
                    # a.rgb.assign(*bp['transmittance'])
                else:
                    a = Cattribute()
                    a.activeType = MAP_TYPE_VALUE
                    a.value = bp['single_sided_value']
                r.setScatteringThickness(a)
                r.setScatteringThicknessRange(bp['single_sided_min'], bp['single_sided_max'])
            
            # coating
            cp = d['coating']
            if(cp['enabled']):
                c = b.addCoating()
                
                if(cp['thickness_map_enabled']):
                    # # a = texture(cp['thickness_map'], s, )
                    # t = texture(cp['thickness_map'], s, )
                    # a = Cattribute()
                    # a.textureMap = t
                    a = Cattribute()
                    a.activeType = MAP_TYPE_BITMAP
                    t = texture(cp['thickness_map'], s, )
                    if(t is not None):
                        a.textureMap = t
                    a.value = cp['thickness']
                    # a.rgb.assign(*bp['transmittance'])
                else:
                    a = Cattribute()
                    a.activeType = MAP_TYPE_VALUE
                    a.value = cp['thickness']
                c.setThickness(a)
                c.setThicknessRange(cp['thickness_map_min'], cp['thickness_map_max'])
                
                r = c.getReflectance()
                if(cp['ior'] == 1):
                    # measured data
                    r.setActiveIorMode(1)
                    r.setComplexIor(cp['complex_ior'])
                else:
                    if(cp['reflectance_0_map_enabled']):
                        # # a = texture(cp['reflectance_0_map'], s, )
                        # t = texture(cp['reflectance_0_map'], s, )
                        # a = Cattribute()
                        # a.textureMap = t
                        a = Cattribute()
                        a.activeType = MAP_TYPE_BITMAP
                        t = texture(cp['reflectance_0_map'], s, )
                        if(t is not None):
                            a.textureMap = t
                        # a.value = bp['thickness']
                        a.rgb.assign(*cp['reflectance_0'])
                    else:
                        a = Cattribute()
                        a.activeType = MAP_TYPE_RGB
                        a.rgb.assign(*cp['reflectance_0'])
                    r.setAttribute('color', a)
                    
                    if(cp['reflectance_90_map_enabled']):
                        # # a = texture(cp['reflectance_90_map'], s, )
                        # t = texture(cp['reflectance_90_map'], s, )
                        # a = Cattribute()
                        # a.textureMap = t
                        a = Cattribute()
                        a.activeType = MAP_TYPE_BITMAP
                        t = texture(cp['reflectance_90_map'], s, )
                        if(t is not None):
                            a.textureMap = t
                        # a.value = bp['thickness']
                        a.rgb.assign(*cp['reflectance_90'])
                    else:
                        a = Cattribute()
                        a.activeType = MAP_TYPE_RGB
                        a.rgb.assign(*cp['reflectance_90'])
                    r.setAttribute('color.tangential', a)
                    r.setIOR(cp['nd'], 1.0, )
                    if(cp['force_fresnel']):
                        r.enableForceFresnel(True)
                    r.setConductor(cp['k'])
                    if(cp['r2_enabled']):
                        r.setFresnelCustom(cp['r2_falloff_angle'], 0.0, True, )
        
        def add_emitter(d, l):
            e = l.createEmitter()
            
            if(d['type'] == 0):
                e.setLobeType(EMISSION_LOBE_DEFAULT)
            elif(d['type'] == 1):
                e.setLobeType(EMISSION_LOBE_IES)
                e.setLobeIES(d['ies_data'])
                e.setIESLobeIntensity(d['ies_intensity'])
            elif(d['type'] == 2):
                e.setLobeType(EMISSION_LOBE_SPOTLIGHT)
                if(d['spot_map'] is not None):
                    t = texture(d['spot_map'], s)
                    if(t is not None):
                        e.setLobeImageProjectedMap(d['spot_map_enabled'], t)
                e.setSpotConeAngle(d['spot_cone_angle'])
                e.setSpotFallOffAngle(d['spot_falloff_angle'])
                e.setSpotFallOffType(d['spot_falloff_type'])
                e.setSpotBlur(d['spot_blur'])
            if(d['emission'] == 0):
                e.setActiveEmissionType(EMISSION_TYPE_PAIR)
                ep = CemitterPair()
                # c = Crgb8()
                c = Crgb()
                c.assign(*d['color'])
                # ep.rgb.assign(c.toRGB())
                ep.rgb.assign(c)
                ep.temperature = d['color_black_body']
                ep.watts = d['luminance_power']
                ep.luminousEfficacy = d['luminance_efficacy']
                ep.luminousPower = d['luminance_output']
                ep.illuminance = d['luminance_output']
                ep.luminousIntensity = d['luminance_output']
                ep.luminance = d['luminance_output']
                e.setPair(ep)
                
                if(d['luminance'] == 0):
                    u = EMISSION_UNITS_WATTS_AND_LUMINOUS_EFFICACY
                elif(d['luminance'] == 1):
                    u = EMISSION_UNITS_LUMINOUS_POWER
                elif(d['luminance'] == 2):
                    u = EMISSION_UNITS_ILLUMINANCE
                elif(d['luminance'] == 3):
                    u = EMISSION_UNITS_LUMINOUS_INTENSITY
                elif(d['luminance'] == 4):
                    u = EMISSION_UNITS_LUMINANCE
                if(d['color_black_body_enabled']):
                    e.setActivePair(EMISSION_COLOR_TEMPERATURE, u)
                else:
                    e.setActivePair(EMISSION_RGB, u)
            
            elif(d['emission'] == 1):
                e.setActiveEmissionType(EMISSION_TYPE_TEMPERATURE)
                e.setTemperature(d['temperature_value'])
            elif(d['emission'] == 2):
                e.setActiveEmissionType(EMISSION_TYPE_MXI)
                a = Cattribute()
                a.activeType = MAP_TYPE_BITMAP
                t = texture(d['hdr_map'], s)
                if(t is not None):
                    a.textureMap = t
                a.value = d['hdr_intensity']
                e.setMXI(a)
            
            e.setState(True)
        
        def add_layer(d, m):
            l = m.addLayer()
            l.setName(d['name'])
            
            lpd = d['layer_props']
            if(not lpd['visible']):
                l.setEnabled(False)
            if(lpd['blending'] == 1):
                l.setStackedBlendingMode(1)
            if(lpd['opacity_map_enabled']):
                # a = texture(lpd['opacity_map'], s, )
                a = Cattribute()
                a.activeType = MAP_TYPE_BITMAP
                t = texture(lpd['opacity_map'], s, )
                if(t is not None):
                    a.textureMap = t
                a.value = lpd['opacity']
            else:
                a = Cattribute()
                a.activeType = MAP_TYPE_VALUE
                a.value = lpd['opacity']
            l.setAttribute('weight', a)
            
            epd = d['emitter']
            if(epd['enabled']):
                add_emitter(epd, l)
        
            for b in d['bsdfs']:
                add_bsdf(b, l)
        
        global_props(d['global_props'], m)
        displacement(d['displacement'], m)
        for layer in d['layers']:
            add_layer(layer, m)
        
        return m
    
    def material(self, d, ):
        s = self.mxs
        if(d['subtype'] == 'EXTERNAL'):
            if(d['path'] == ''):
                m = self.material_placeholder(d['name'])
            else:
                m = self.material_external(d)
                
                if(d['override']):
                    # global properties
                    if(d['override_map']):
                        t = self.texture(d['override_map'])
                        if(t is not None):
                            m.setGlobalMap(t)
                    
                    if(d['bump']):
                        a = Cattribute()
                        a.activeType = MAP_TYPE_BITMAP
                        t = self.texture(d['bump_map'])
                        if(t is not None):
                            a.textureMap = t
                        a.value = d['bump_value']
                        m.setAttribute('bump', a)
                    
                    m.setDispersion(d['dispersion'])
                    m.setMatteShadow(d['shadow'])
                    m.setMatte(d['matte'])
                    m.setNestedPriority(d['priority'])
                    
                    c = Crgb()
                    cc = [c / 255 for c in d['id']]
                    c.assign(*cc)
                    m.setColorID(c)
        
        elif(d['subtype'] == 'EXTENSION'):
            if(d['use'] == 'EMITTER'):
                m = s.createMaterial(d['name'])
                l = m.addLayer()
                e = l.createEmitter()
                
                if(d['emitter_type'] == 0):
                    e.setLobeType(EMISSION_LOBE_DEFAULT)
                elif(d['emitter_type'] == 1):
                    e.setLobeType(EMISSION_LOBE_IES)
                    e.setLobeIES(d['emitter_ies_data'])
                    e.setIESLobeIntensity(d['emitter_ies_intensity'])
                elif(d['emitter_type'] == 2):
                    # e.setLobeType(EMISSION_LOBE_BITMAP)
                    e.setLobeType(EMISSION_LOBE_SPOTLIGHT)
                    if(d['emitter_spot_map'] is not None):
                        t = self.texture(d['emitter_spot_map'])
                        if(t is not None):
                            e.setLobeImageProjectedMap(d['emitter_spot_map_enabled'], t)
                    e.setSpotConeAngle(d['emitter_spot_cone_angle'])
                    e.setSpotFallOffAngle(d['emitter_spot_falloff_angle'])
                    e.setSpotFallOffType(d['emitter_spot_falloff_type'])
                    e.setSpotBlur(d['emitter_spot_blur'])
                
                if(d['emitter_emission'] == 0):
                    e.setActiveEmissionType(EMISSION_TYPE_PAIR)
                    
                    ep = CemitterPair()
                    c = Crgb8()
                    c.assign(*d['emitter_color'])
                    ep.rgb.assign(c.toRGB())
                    ep.temperature = d['emitter_color_black_body']
                    ep.watts = d['emitter_luminance_power']
                    ep.luminousEfficacy = d['emitter_luminance_efficacy']
                    ep.luminousPower = d['emitter_luminance_output']
                    ep.illuminance = d['emitter_luminance_output']
                    ep.luminousIntensity = d['emitter_luminance_output']
                    ep.luminance = d['emitter_luminance_output']
                    e.setPair(ep)
                    
                    if(d['emitter_luminance'] == 0):
                        u = EMISSION_UNITS_WATTS_AND_LUMINOUS_EFFICACY
                    elif(d['emitter_luminance'] == 1):
                        u = EMISSION_UNITS_LUMINOUS_POWER
                    elif(d['emitter_luminance'] == 2):
                        u = EMISSION_UNITS_ILLUMINANCE
                    elif(d['emitter_luminance'] == 3):
                        u = EMISSION_UNITS_LUMINOUS_INTENSITY
                    elif(d['emitter_luminance'] == 4):
                        u = EMISSION_UNITS_LUMINANCE
                    if(d['emitter_color_black_body_enabled']):
                        e.setActivePair(EMISSION_COLOR_TEMPERATURE, u)
                    else:
                        e.setActivePair(EMISSION_RGB, u)
                
                elif(d['emitter_emission'] == 1):
                    e.setActiveEmissionType(EMISSION_TYPE_TEMPERATURE)
                    e.setTemperature(d['emitter_temperature_value'])
                elif(d['emitter_emission'] == 2):
                    e.setActiveEmissionType(EMISSION_TYPE_MXI)
                    a = Cattribute()
                    a.activeType = MAP_TYPE_BITMAP
                    t = self.texture(d['emitter_hdr_map'])
                    if(t is not None):
                        a.textureMap = t
                    a.value = d['emitter_hdr_intensity']
                    e.setMXI(a)
                
                e.setState(True)
            else:
                m = CextensionManager.instance()
                m.loadAllExtensions()
                if(d['use'] == 'AGS'):
                    e = m.createDefaultMaterialModifierExtension('AGS')
                    p = e.getExtensionData()
                    
                    c = Crgb8()
                    c.assign(*d['ags_color'])
                    p.setRgb('Color', c.toRGB())
                    p.setFloat('Reflection', d['ags_reflection'])
                    p.setUInt('Type', d['ags_type'])
                
                elif(d['use'] == 'OPAQUE'):
                    e = m.createDefaultMaterialModifierExtension('Opaque')
                    p = e.getExtensionData()
                    
                    p.setByte('Color Type', d['opaque_color_type'])
                    c = Crgb8()
                    c.assign(*d['opaque_color'])
                    p.setRgb('Color', c.toRGB())
                    self.texture_data_to_mxparams('Color Map', d['opaque_color_map'], p, )
                    
                    p.setByte('Shininess Type', d['opaque_shininess_type'])
                    p.setFloat('Shininess', d['opaque_shininess'])
                    self.texture_data_to_mxparams('Shininess Map', d['opaque_shininess_map'], p, )
                    
                    p.setByte('Roughness Type', d['opaque_roughness_type'])
                    p.setFloat('Roughness', d['opaque_roughness'])
                    self.texture_data_to_mxparams('Roughness Map', d['opaque_roughness_map'], p, )
                    
                    p.setByte('Clearcoat', d['opaque_clearcoat'])
                
                elif(d['use'] == 'TRANSPARENT'):
                    e = m.createDefaultMaterialModifierExtension('Transparent')
                    p = e.getExtensionData()
                    
                    p.setByte('Color Type', d['transparent_color_type'])
                    c = Crgb8()
                    c.assign(*d['transparent_color'])
                    p.setRgb('Color', c.toRGB())
                    self.texture_data_to_mxparams('Color Map', d['transparent_color_map'], p, )
                    
                    p.setFloat('Ior', d['transparent_ior'])
                    p.setFloat('Transparency', d['transparent_transparency'])
                    
                    p.setByte('Roughness Type', d['transparent_roughness_type'])
                    p.setFloat('Roughness', d['transparent_roughness'])
                    self.texture_data_to_mxparams('Roughness Map', d['transparent_roughness_map'], p, )
                    
                    p.setFloat('Specular Tint', d['transparent_specular_tint'])
                    p.setFloat('Dispersion', d['transparent_dispersion'])
                    p.setByte('Clearcoat', d['transparent_clearcoat'])
                
                elif(d['use'] == 'METAL'):
                    e = m.createDefaultMaterialModifierExtension('Metal')
                    p = e.getExtensionData()
                    
                    p.setUInt('IOR', d['metal_ior'])
                    
                    p.setFloat('Tint', d['metal_tint'])
                    
                    p.setByte('Color Type', d['metal_color_type'])
                    c = Crgb8()
                    c.assign(*d['metal_color'])
                    p.setRgb('Color', c.toRGB())
                    self.texture_data_to_mxparams('Color Map', d['metal_color_map'], p, )
                    
                    p.setByte('Roughness Type', d['metal_roughness_type'])
                    p.setFloat('Roughness', d['metal_roughness'])
                    self.texture_data_to_mxparams('Roughness Map', d['metal_roughness_map'], p, )
                    
                    p.setByte('Anisotropy Type', d['metal_anisotropy_type'])
                    p.setFloat('Anisotropy', d['metal_anisotropy'])
                    self.texture_data_to_mxparams('Anisotropy Map', d['metal_anisotropy_map'], p, )
                    
                    p.setByte('Angle Type', d['metal_angle_type'])
                    p.setFloat('Angle', d['metal_angle'])
                    self.texture_data_to_mxparams('Angle Map', d['metal_angle_map'], p, )
                    
                    p.setByte('Dust Type', d['metal_dust_type'])
                    p.setFloat('Dust', d['metal_dust'])
                    self.texture_data_to_mxparams('Dust Map', d['metal_dust_map'], p, )
                    
                    p.setByte('Perforation Enabled', d['metal_perforation_enabled'])
                    self.texture_data_to_mxparams('Perforation Map', d['metal_perforation_map'], p, )
                
                elif(d['use'] == 'TRANSLUCENT'):
                    e = m.createDefaultMaterialModifierExtension('Translucent')
                    p = e.getExtensionData()
                    
                    p.setFloat('Scale', d['translucent_scale'])
                    p.setFloat('Ior', d['translucent_ior'])
                    
                    p.setByte('Color Type', d['translucent_color_type'])
                    c = Crgb8()
                    c.assign(*d['translucent_color'])
                    p.setRgb('Color', c.toRGB())
                    self.texture_data_to_mxparams('Color Map', d['translucent_color_map'], p, )
                    
                    p.setFloat('Hue Shift', d['translucent_hue_shift'])
                    p.setByte('Invert Hue', d['translucent_invert_hue'])
                    p.setFloat('Vibrance', d['translucent_vibrance'])
                    p.setFloat('Density', d['translucent_density'])
                    p.setFloat('Opacity', d['translucent_opacity'])
                    
                    p.setByte('Roughness Type', d['translucent_roughness_type'])
                    p.setFloat('Roughness', d['translucent_roughness'])
                    self.texture_data_to_mxparams('Roughness Map', d['translucent_roughness_map'], p, )
                    
                    p.setFloat('Specular Tint', d['translucent_specular_tint'])
                    p.setByte('Clearcoat', d['translucent_clearcoat'])
                    p.setFloat('Clearcoat Ior', d['translucent_clearcoat_ior'])
                
                elif(d['use'] == 'CARPAINT'):
                    e = m.createDefaultMaterialModifierExtension('Car Paint')
                    p = e.getExtensionData()
                    
                    c = Crgb8()
                    c.assign(*d['carpaint_color'])
                    p.setRgb('Color', c.toRGB())
                    
                    p.setFloat('Metallic', d['carpaint_metallic'])
                    p.setFloat('Topcoat', d['carpaint_topcoat'])
                
                elif(d['use'] == 'HAIR'):
                    e = m.createDefaultMaterialModifierExtension('Hair')
                    p = e.getExtensionData()
                    
                    p.setByte('Color Type', d['hair_color_type'])
                    
                    c = Crgb8()
                    c.assign(*d['hair_color'])
                    p.setRgb('Color', c.toRGB())
                    self.texture_data_to_mxparams('Color Map', d['hair_color_map'], p, )
                    
                    self.texture_data_to_mxparams('Root-Tip Map', d['hair_root_tip_map'], p, )
                    
                    p.setByte('Root-Tip Weight Type', d['hair_root_tip_weight_type'])
                    p.setFloat('Root-Tip Weight', d['hair_root_tip_weight'])
                    self.texture_data_to_mxparams('Root-Tip Weight Map', d['hair_root_tip_weight_map'], p, )
                    
                    p.setFloat('Primary Highlight Strength', d['hair_primary_highlight_strength'])
                    p.setFloat('Primary Highlight Spread', d['hair_primary_highlight_spread'])
                    c = Crgb8()
                    c.assign(*d['hair_primary_highlight_tint'])
                    p.setRgb('Primary Highlight Tint', c.toRGB())
                    
                    p.setFloat('Secondary Highlight Strength', d['hair_secondary_highlight_strength'])
                    p.setFloat('Secondary Highlight Spread', d['hair_secondary_highlight_spread'])
                    c = Crgb8()
                    c.assign(*d['hair_secondary_highlight_tint'])
                    p.setRgb('Secondary Highlight Tint', c.toRGB())
                
                m = s.createMaterial(d['name'])
                m.applyMaterialModifierExtension(p)
                
                # global properties
                if(d['override_map']):
                    t = self.texture(d['override_map'])
                    if(t is not None):
                        m.setGlobalMap(t)
                
                if(d['bump']):
                    a = Cattribute()
                    a.activeType = MAP_TYPE_BITMAP
                    t = self.texture(d['bump_map'])
                    if(t is not None):
                        a.textureMap = t
                    a.value = d['bump_value']
                    m.setAttribute('bump', a)
                
                m.setDispersion(d['dispersion'])
                m.setMatteShadow(d['shadow'])
                m.setMatte(d['matte'])
                
                m.setNestedPriority(d['priority'])
                
                c = Crgb()
                cc = [c / 255 for c in d['id']]
                c.assign(*cc)
                m.setColorID(c)
        elif(d['subtype'] == 'CUSTOM'):
            m = self.material_custom(d)
        else:
            raise TypeError("Material '{}' {} is unknown type".format(d['name'], d['subtype']))
    
    def get_material(self, n, ):
        """get material by name from scene, if material is missing, create and return placeholder"""
        def get_material_names(s):
            it = CmaxwellMaterialIterator()
            o = it.first(s)
            l = []
            while not o.isNull():
                name = o.getName()
                l.append(name)
                o = it.next()
            return l
        
        s = self.mxs
        names = get_material_names(s)
        m = None
        if(n in names):
            m = s.getMaterial(n)
        if(m is None):
            # should not happen because i stopped changing material names.. but i leave it here
            m = self.material_placeholder()
        return m
    
    def camera(self, props, steps, active=False, lens_extra=None, response=None, region=None, custom_bokeh=(1.0, 0.0, False), cut_planes=(0.0, 1e7, False), shift_lens=(0.0, 0.0), ):
        """Create camera.
        props           (string name, int nSteps, float shutter, float filmWidth, float filmHeight, float iso, int diaphragmType, float angle,
                         int nBlades, float fps, int xRes, int yRes, float pixelAspect, int lensType, int projectionType)
        steps           [(int iStep, [3 float] origin, [3 float] focalPoint, [3 float] up, float focalLength, float fStop, bool focalLengthNeedCorrection), ..., ]
        active          bool
        lens_extra      float or None
        response        string or None
        region          (float x1, float y1, float x2, float y2, string type) or None
        custom_bokeh    (float ratio, float angle, bool enabled) or None
        cut_planes      (float near, float far, bool enabled) or None
        shift_lens      (float x, float y) or None
        """
        s = self.mxs
        c = s.addCamera(*props)
        for step in steps:
            l = list(step[:])
            l[1] = Cvector(*l[1])
            l[2] = Cvector(*l[2])
            l[3] = Cvector(*l[3])
            c.setStep(*l)
        
        # TYPE_THIN_LENS, TYPE_PINHOLE, TYPE_ORTHO
        if(lens_extra is not None):
            if(props[13] == TYPE_FISHEYE):
                c.setFishLensProperties(lens_extra)
            if(props[13] == TYPE_SPHERICAL):
                c.setSphericalLensProperties(lens_extra)
            if(props[13] == TYPE_CYLINDRICAL):
                c.setCylindricalLensProperties(lens_extra)
        if(response is not None):
            c.setCameraResponsePreset(response)
        if(custom_bokeh is not None):
            c.setCustomBokeh(*custom_bokeh)
        if(cut_planes is not None):
            c.setCutPlanes(*cut_planes)
        if(shift_lens is not None):
            c.setShiftLens(*shift_lens)
        if(region is not None):
            c.setScreenRegion(*region)
        
        if(active):
            c.setActive()
        return c
    
    def empty(self, name, matrix, object_props=None, ):
        """Create empty object.
        name            string
        matrix          (((3 float), (3 float), (3 float), (3 float)), ((3 float), (3 float), (3 float), (3 float)), (3 float), (3 float), (3 float)) - base, pivot, location, rotation, scale
        object_props    (bool hide, float opacity, tuple cid=(int, int, int), bool hcam, bool hcamsc, bool hgi, bool hrr, bool hzcp, ) or None
        """
        s = self.mxs
        o = s.createMesh(name, 0, 0, 0, 0, )
        self.set_base_and_pivot(o, matrix, )
        if(object_props is not None):
            self.set_object_props(o, *object_props)
        return o
    
    def mesh(self, name, matrix, num_positions, vertices, normals, triangles, triangle_normals, uv_channels, object_props=None, num_materials=0, materials=[], triangle_materials=None, backface_material=None, ):
        """Create mesh object.
        name                string
        base                ((3 float), (3 float), (3 float), (3 float))
        pivot               ((3 float), (3 float), (3 float), (3 float))
        num_positions       int
        vertices            [[(float x, float y, float z), ..., ], [...], ]
        normals             [[(float x, float y, float z), ..., ], [...], ]
        triangles           [(int iv0, int iv1, int iv2, int in0, int in1, int in2, ), ..., ], ]   # (3x vertex index, 3x normal index)
        triangle_normals    [[(float x, float y, float z), ..., ], [...], ]
        uv_channels         [[(float u1, float v1, float w1, float u2, float v2, float w2, float u3, float v3, float w3, ), ..., ], ..., ] or None      # ordered by uv index and ordered by triangle index
        num_materials       int
        object_props        (bool hide, float opacity, tuple cid=(int, int, int), bool hcam, bool hcamsc, bool hgi, bool hrr, bool hzcp, ) or None
        materials           [(string path, bool embed), ..., ] or None
        triangle_materials  [(int tri_id, int mat_id), ..., ] or None
        backface_material   (string path, bool embed) or None
        """
        s = self.mxs
        o = s.createMesh(name, len(vertices[0]), len(normals[0]) + len(triangle_normals[0]), len(triangles), num_positions)
        if(uv_channels is not None):
            for i in range(len(uv_channels)):
                o.addChannelUVW(i)
        an = 0
        for ip in range(num_positions):
            verts = vertices[ip]
            norms = normals[ip]
            for i, loc in enumerate(verts):
                o.setVertex(i, ip, Cvector(*loc), )
                o.setNormal(i, ip, Cvector(*norms[i]), )
                an += 1
        for ip in range(num_positions):
            trinorms = triangle_normals[ip]
            for i, nor in enumerate(trinorms):
                o.setNormal(an + i, ip, Cvector(*nor), )
        for i, tri in enumerate(triangles):
            o.setTriangle(i, *tri)
        if(uv_channels is not None):
            for iuv, uv in enumerate(uv_channels):
                for it, t in enumerate(uv):
                    o.setTriangleUVW(it, iuv, *t)
        
        self.set_base_and_pivot(o, matrix, )
        if(object_props is not None):
            self.set_object_props(o, *object_props)
        
        if(materials is not None):
            # if(num_materials > 1):
            #     # multi material
            #     mats = []
            #     for mi in range(num_materials):
            #         if(type(materials[mi][0]) is dict):
            #             mat = self.ext_material(materials[mi][0])
            #         else:
            #             mat = self.load_material(*materials[mi])
            #         if(mat is None):
            #             mat = self.material_placeholder()
            #         mats.append(mat)
            #     for tid, mid in triangle_materials:
            #         o.setTriangleMaterial(tid, mats[mid])
            # elif(num_materials == 1):
            #     # single material
            #     if(type(materials[0][0]) is dict):
            #         mat = self.ext_material(materials[0][0])
            #     else:
            #         mat = self.load_material(*materials[0])
            #     if(mat is not None):
            #         # set for whole object, no need to care about triangles
            #         o.setMaterial(mat)
            
            if(num_materials > 1):
                # multi material
                mats = []
                # for n in materials:
                #     mat = self.get_material(n)
                #     mats.append(mat)
                for i in range(num_materials):
                    try:
                        n = materials[i]
                        mat = self.get_material(n)
                    except:
                        mat = self.material_placeholder()
                    mats.append(mat)
                
                for tid, mid in triangle_materials:
                    o.setTriangleMaterial(tid, mats[mid])
            else:
                # single material
                if(len(materials) == 1):
                    if(materials[0] != ''):
                        mat = self.get_material(materials[0])
                        o.setMaterial(mat)
        else:
            # no material
            pass
        
        if(backface_material is not None):
            if(backface_material != ''):
                # only single backface material
                mat = self.get_material(backface_material)
                o.setBackfaceMaterial(mat)
        
        return o
    
    def instance(self, name, instanced_name, matrix, object_props=None, materials=None, backface_material=None, ):
        """Create instance of mesh object. Instanced object must exist in scene.
        name                string
        instanced_name      string
        base                ((3 float), (3 float), (3 float), (3 float))
        pivot               ((3 float), (3 float), (3 float), (3 float))
        object_props        (bool hide, float opacity, tuple cid=(int, int, int), bool hcam, bool hcamsc, bool hgi, bool hrr, bool hzcp, ) or None
        material            (string path, bool embed) or None
        backface_material   (string path, bool embed) or None
        """
        s = self.mxs
        bo = s.getObject(instanced_name)
        o = s.createInstancement(name, bo)
        
        self.set_base_and_pivot(o, matrix, )
        if(object_props is not None):
            self.set_object_props(o, *object_props)
        
        # if(material is not None):
        #     if(type(material[0]) is dict):
        #         m = self.ext_material(material[0])
        #     else:
        #         m = self.load_material(*material)
        #     if(m is not None):
        #         o.setMaterial(m)
        # if(backface_material is not None):
        #     m = self.load_material(*backface_material)
        #     if(m is not None):
        #         o.setBackfaceMaterial(m)
        
        if(materials is not None):
            if(len(materials) > 1):
                # multi material instances inherits material from base object
                pass
            else:
                # single material, and i think (not sure) i can't make instance with different material than base in blender..
                if(len(materials) == 1):
                    if(materials[0] != ''):
                        mat = self.get_material(materials[0])
                        o.setMaterial(mat)
        
        if(backface_material is not None):
            if(backface_material != ''):
                mat = self.get_material(backface_material)
                o.setBackfaceMaterial(mat)
        
        return o
    
    def reference(self, name, path, flags, matrix, object_props=None, material=None, backface_material=None, ):
        """Create MXS reference object.
        name            string
        path            string (path)
        flags           [bool, bool, bool, bool]
        base            ((3 float), (3 float), (3 float), (3 float))
        pivot           ((3 float), (3 float), (3 float), (3 float))
        object_props    (bool hide, float opacity, tuple cid=(int, int, int), bool hcam, bool hcamsc, bool hgi, bool hrr, bool hzcp, ) or None
        """
        s = self.mxs
        o = s.createMesh(name, 0, 0, 0, 0, )
        o.setReferencedScenePath(path)
        if(flags[0]):
            o.setReferencedOverrideFlags(FLAG_OVERRIDE_HIDE)
        if(flags[1]):
            o.setReferencedOverrideFlags(FLAG_OVERRIDE_HIDE_TO_CAMERA)
        if(flags[2]):
            o.setReferencedOverrideFlags(FLAG_OVERRIDE_HIDE_TO_REFL_REFR)
        if(flags[3]):
            o.setReferencedOverrideFlags(FLAG_OVERRIDE_HIDE_TO_GI)
        self.set_base_and_pivot(o, matrix, )
        if(object_props is not None):
            self.set_object_props(o, *object_props)
        if(material is not None):
            if(material != ''):
                mat = self.get_material(material)
                o.setMaterial(mat)
        if(backface_material is not None):
            if(backface_material != ''):
                mat = self.get_material(backface_material)
                o.setBackfaceMaterial(mat)
        
        return o
    
    def hierarchy(self, tree, ):
        """Set hierarchy of all objects at once.
        tree    [(obj_name, parent_name or None, ), ..., ]
        """
        s = self.mxs
        for on, pn, _ in tree:
            if(pn is not None):
                o = s.getObject(on)
                p = s.getObject(pn)
                o.setParent(p)
    
    def environment(self, env_type=None, sky_type=None, sky=None, dome=None, sun_type=None, sun=None, ibl=None, ):
        """Set Environment properties.
        env_type    string or None      PHYSICAL_SKY, IMAGE_BASED, NONE
        sky_type    string or None      PHYSICAL, CONSTANT
        sky         dict or None        {sky_use_preset         bool
                                         sky_preset             string (path)
                                         sky_intensity          float
                                         sky_planet_refl        float
                                         sky_ozone              float
                                         sky_water              float
                                         sky_turbidity_coeff    float
                                         sky_wavelength_exp     float
                                         sky_reflectance        float
                                         sky_asymmetry          float}
        dome        dict or None        {dome_intensity         float
                                         dome_zenith            [float, float, float]
                                         dome_horizon           [float, float, float]
                                         dome_mid_point         float}
        sun_type    string or None      DISABLED, PHYSICAL, CUSTOM
        sun         dict or None        {sun_power                      float
                                         sun_radius_factor              float
                                         sun_temp                       float
                                         sun_color                      [float, float, float]
                                         sun_location_type              string      LATLONG, ANGLES, DIRECTION
                                         sun_latlong_lat                float
                                         sun_latlong_lon                float
                                         sun_date                       string
                                         sun_time                       string
                                         sun_latlong_gmt                int
                                         sun_latlong_gmt_auto           bool
                                         sun_latlong_ground_rotation    float
                                         sun_angles_zenith              float
                                         sun_angles_azimuth             float
                                         sun_dir_x                      float
                                         sun_dir_y                      float
                                         sun_dir_z                      float}
        ibl         dict or None        {ibl_intensity          float
                                         ibl_interpolation      bool
                                         ibl_screen_mapping     bool
                                         ibl_bg_type            string      HDR_IMAGE, ACTIVE_SKY, DISABLED
                                         ibl_bg_map             string (path)
                                         ibl_bg_intensity       float
                                         ibl_bg_scale_x         float
                                         ibl_bg_scale_y         float
                                         ibl_bg_offset_x        float
                                         ibl_bg_offset_y        float
                                         ibl_refl_type          string      HDR_IMAGE, ACTIVE_SKY, DISABLED
                                         ibl_refl_map           string (path)
                                         ibl_refl_intensity     float
                                         ibl_refl_scale_x       float
                                         ibl_refl_scale_y       float
                                         ibl_refl_offset_x      float
                                         ibl_refl_offset_y      float
                                         ibl_refr_type          string      HDR_IMAGE, ACTIVE_SKY, DISABLED
                                         ibl_refr_map           string (path)
                                         ibl_refr_intensity     float
                                         ibl_refr_scale_x       float
                                         ibl_refr_scale_y       float
                                         ibl_refr_offset_x      float
                                         ibl_refr_offset_y      float
                                         ibl_illum_type         string      HDR_IMAGE, ACTIVE_SKY, DISABLED
                                         ibl_illum_map          string (path)
                                         ibl_illum_intensity    float
                                         ibl_illum_scale_x      float
                                         ibl_illum_scale_y      float
                                         ibl_illum_offset_x     float
                                         ibl_illum_offset_y     float}
        """
        s = self.mxs
        env = s.getEnvironment()
        if(env_type == 'PHYSICAL_SKY' or env_type == 'IMAGE_BASED'):
            if(sky_type is not None):
                env.setActiveSky(sky_type)
                if(sky_type == 'PHYSICAL'):
                    if(not sky["sky_use_preset"]):
                        env.setPhysicalSkyAtmosphere(sky["sky_intensity"],
                                                     sky["sky_ozone"],
                                                     sky["sky_water"],
                                                     sky["sky_turbidity_coeff"],
                                                     sky["sky_wavelength_exp"],
                                                     sky["sky_reflectance"],
                                                     sky["sky_asymmetry"],
                                                     sky["sky_planet_refl"], )
                    else:
                        env.loadSkyFromPreset(sky["sky_preset"])
                    
                    sc = Crgb()
                    sc.assign(*[c / 255 for c in sun['sun_color']])
                    if(sun_type == 'PHYSICAL'):
                        env.setSunProperties(SUN_PHYSICAL, sun["sun_temp"], sun["sun_power"], sun["sun_radius_factor"], sc)
                    elif(sun_type == 'CUSTOM'):
                        env.setSunProperties(SUN_CONSTANT, sun["sun_temp"], sun["sun_power"], sun["sun_radius_factor"], sc)
                    else:
                        # sun_type == 'DISABLED' or sun_type == None
                        env.setSunProperties(SUN_DISABLED, sun["sun_temp"], sun["sun_power"], sun["sun_radius_factor"], sc)
                    
                    if(sun['sun_location_type'] == 'LATLONG'):
                        env.setSunPositionType(0)
                        l = sun["sun_date"].split(".")
                        date = datetime.date(int(l[2]), int(l[1]), int(l[0]))
                        day = int(date.timetuple().tm_yday)
                        l = sun["sun_time"].split(":")
                        hour = int(l[0])
                        minute = int(l[1])
                        time = hour + (minute / 60)
                        env.setSunLongitudeAndLatitude(sun["sun_latlong_lon"], sun["sun_latlong_lat"], sun["sun_latlong_gmt"], day, time)
                        env.setSunRotation(sun["sun_latlong_ground_rotation"])
                    elif(sun['sun_location_type'] == 'ANGLES'):
                        env.setSunPositionType(1)
                        env.setSunAngles(sun["sun_angles_zenith"], sun["sun_angles_azimuth"])
                    elif(sun['sun_location_type'] == 'DIRECTION'):
                        env.setSunPositionType(2)
                        env.setSunDirection(Cvector(sun["sun_dir_x"], sun["sun_dir_y"], sun["sun_dir_z"]))
                
                elif(sky_type == 'CONSTANT'):
                    hc = Crgb()
                    hc.assign(*[c / 255 for c in dome['dome_horizon']])
                    zc = Crgb()
                    zc.assign(*[c / 255 for c in dome['dome_zenith']])
                    env.setSkyConstant(dome["dome_intensity"], hc, zc, dome['dome_mid_point'])
            
            if(env_type == 'IMAGE_BASED'):
                env.enableEnvironment(True)
            
            def state(s):
                # channel state: 0 = Disabled;  1 = Enabled; 2 = Use active sky instead.
                if(s == 'HDR_IMAGE'):
                    return 1
                if(s == 'ACTIVE_SKY'):
                    return 2
                if(s == 'SAME_AS_BG'):
                    # same as bg, set the same values as in bg layer
                    return 3
                return 0
            
            if(ibl is not None):
                env.setEnvironmentWeight(ibl["ibl_intensity"])
                
                s = state(ibl["ibl_bg_type"])
                env.setEnvironmentLayer(IBL_LAYER_BACKGROUND, ibl["ibl_bg_map"], s, not ibl["ibl_screen_mapping"], not ibl["ibl_interpolation"], ibl["ibl_bg_intensity"], ibl["ibl_bg_scale_x"], ibl["ibl_bg_scale_y"], ibl["ibl_bg_offset_x"], ibl["ibl_bg_offset_y"], )
                s = state(ibl["ibl_refl_type"])
                if(s == 3):
                    s = state(ibl["ibl_bg_type"])
                    env.setEnvironmentLayer(IBL_LAYER_REFLECTION, ibl["ibl_bg_map"], s, not ibl["ibl_screen_mapping"], not ibl["ibl_interpolation"], ibl["ibl_bg_intensity"], ibl["ibl_bg_scale_x"], ibl["ibl_bg_scale_y"], ibl["ibl_bg_offset_x"], ibl["ibl_bg_offset_y"], )
                else:
                    env.setEnvironmentLayer(IBL_LAYER_REFLECTION, ibl["ibl_refl_map"], s, not ibl["ibl_screen_mapping"], not ibl["ibl_interpolation"], ibl["ibl_refl_intensity"], ibl["ibl_refl_scale_x"], ibl["ibl_refl_scale_y"], ibl["ibl_refl_offset_x"], ibl["ibl_refl_offset_y"], )
                s = state(ibl["ibl_refr_type"])
                if(s == 3):
                    s = state(ibl["ibl_bg_type"])
                    env.setEnvironmentLayer(IBL_LAYER_REFRACTION, ibl["ibl_bg_map"], s, not ibl["ibl_screen_mapping"], not ibl["ibl_interpolation"], ibl["ibl_bg_intensity"], ibl["ibl_bg_scale_x"], ibl["ibl_bg_scale_y"], ibl["ibl_bg_offset_x"], ibl["ibl_bg_offset_y"], )
                else:
                    env.setEnvironmentLayer(IBL_LAYER_REFRACTION, ibl["ibl_refr_map"], s, not ibl["ibl_screen_mapping"], not ibl["ibl_interpolation"], ibl["ibl_refr_intensity"], ibl["ibl_refr_scale_x"], ibl["ibl_refr_scale_y"], ibl["ibl_refr_offset_x"], ibl["ibl_refr_offset_y"], )
                s = state(ibl["ibl_illum_type"])
                if(s == 3):
                    s = state(ibl["ibl_bg_type"])
                    env.setEnvironmentLayer(IBL_LAYER_ILLUMINATION, ibl["ibl_bg_map"], s, not ibl["ibl_screen_mapping"], not ibl["ibl_interpolation"], ibl["ibl_bg_intensity"], ibl["ibl_bg_scale_x"], ibl["ibl_bg_scale_y"], ibl["ibl_bg_offset_x"], ibl["ibl_bg_offset_y"], )
                else:
                    env.setEnvironmentLayer(IBL_LAYER_ILLUMINATION, ibl["ibl_illum_map"], s, not ibl["ibl_screen_mapping"], not ibl["ibl_interpolation"], ibl["ibl_illum_intensity"], ibl["ibl_illum_scale_x"], ibl["ibl_illum_scale_y"], ibl["ibl_illum_offset_x"], ibl["ibl_illum_offset_y"], )
            
        else:
            # env_type == 'NONE' or env_type == None
            env.setActiveSky('')
    
    def parameters(self, scene, materials=None, generals=None, tone=None, simulens=None, illum_caustics=None, other=None, ):
        """Set scene render parameters.
        scene           dict    {cpu_threads        int,
                                 multilight         int,
                                 multilight_type    int,
                                 quality            string      RS1, RS0
                                 sampling_level     float,
                                 time               int, },
        materials       dict    {override           bool,
                                 override_path      string (path),
                                 search_path        string (path), } or None
        generals        dict    {diplacement        bool,
                                 dispersion         bool,
                                 motion_blur        bool, } or None
        tone            dict    {burn               float,
                                 color_space        int,
                                 gamma              float,
                                 sharpness          bool,
                                 sharpness_value    float,
                                 tint               float,
                                 whitepoint         float, } or None
        simulens        dict    {aperture_map       string (path),
                                 devignetting       bool,
                                 devignetting_value float,
                                 diffraction        bool,
                                 diffraction_value  float,
                                 frequency          float,
                                 obstacle_map       string (path),
                                 scattering         bool,
                                 scattering_value   float, } or None
        illum_caustics  dict    {illumination       int,
                                 refl_caustics      int,
                                 refr_caustics      int, } or None
        other           dict    {protect            bool, }
        """
        s = self.mxs
        # s.setRenderParameter('ENGINE', scene["quality"])
        s.setRenderParameter('ENGINE', bytes(scene["quality"], encoding='UTF-8'))
        s.setRenderParameter('NUM THREADS', scene["cpu_threads"])
        s.setRenderParameter('STOP TIME', scene["time"] * 60)
        s.setRenderParameter('SAMPLING LEVEL', scene["sampling_level"])
        s.setRenderParameter('USE MULTILIGHT', scene["multilight"])
        s.setRenderParameter('SAVE LIGHTS IN SEPARATE FILES', scene["multilight_type"])
        
        if(generals is not None):
            s.setRenderParameter('DO MOTION BLUR', generals["motion_blur"])
            s.setRenderParameter('DO DISPLACEMENT', generals["diplacement"])
            s.setRenderParameter('DO DISPERSION', generals["dispersion"])
        
        if(illum_caustics is not None):
            v = illum_caustics['illumination']
            if(v == 3):
                s.setRenderParameter('DO DIRECT LAYER', 0)
                s.setRenderParameter('DO INDIRECT LAYER', 0)
            elif(v == 2):
                s.setRenderParameter('DO DIRECT LAYER', 0)
                s.setRenderParameter('DO INDIRECT LAYER', 1)
            elif(v == 1):
                s.setRenderParameter('DO DIRECT LAYER', 1)
                s.setRenderParameter('DO INDIRECT LAYER', 0)
            else:
                s.setRenderParameter('DO DIRECT LAYER', 1)
                s.setRenderParameter('DO INDIRECT LAYER', 1)
            v = illum_caustics['refl_caustics']
            if(v == 3):
                s.setRenderParameter('DO DIRECT REFLECTION CAUSTIC LAYER', 0)
                s.setRenderParameter('DO INDIRECT REFLECTION CAUSTIC LAYER', 0)
            elif(v == 2):
                s.setRenderParameter('DO DIRECT REFLECTION CAUSTIC LAYER', 0)
                s.setRenderParameter('DO INDIRECT REFLECTION CAUSTIC LAYER', 1)
            elif(v == 1):
                s.setRenderParameter('DO DIRECT REFLECTION CAUSTIC LAYER', 1)
                s.setRenderParameter('DO INDIRECT REFLECTION CAUSTIC LAYER', 0)
            else:
                s.setRenderParameter('DO DIRECT REFLECTION CAUSTIC LAYER', 1)
                s.setRenderParameter('DO INDIRECT REFLECTION CAUSTIC LAYER', 1)
            v = illum_caustics['refr_caustics']
            if(v == 3):
                s.setRenderParameter('DO DIRECT REFRACTION CAUSTIC LAYER', 0)
                s.setRenderParameter('DO INDIRECT REFRACTION CAUSTIC LAYER', 0)
            elif(v == 2):
                s.setRenderParameter('DO DIRECT REFRACTION CAUSTIC LAYER', 0)
                s.setRenderParameter('DO INDIRECT REFRACTION CAUSTIC LAYER', 1)
            elif(v == 1):
                s.setRenderParameter('DO DIRECT REFRACTION CAUSTIC LAYER', 1)
                s.setRenderParameter('DO INDIRECT REFRACTION CAUSTIC LAYER', 0)
            else:
                s.setRenderParameter('DO DIRECT REFRACTION CAUSTIC LAYER', 1)
                s.setRenderParameter('DO INDIRECT REFRACTION CAUSTIC LAYER', 1)
        
        if(simulens is not None):
            s.setRenderParameter('DO DEVIGNETTING', simulens["devignetting"])
            s.setRenderParameter('DEVIGNETTING', simulens["devignetting_value"])
            s.setRenderParameter('DO SCATTERING_LENS', simulens["scattering"])
            s.setRenderParameter('SCATTERING_LENS', simulens["scattering_value"])
            if(simulens["diffraction"]):
                s.enableDiffraction()
                s.setDiffraction(simulens["diffraction_value"], simulens["frequency"], simulens["aperture_map"], simulens["obstacle_map"])
        
        if(tone is not None):
            s.setRenderParameter('DO SHARPNESS', tone["sharpness"])
            s.setRenderParameter('SHARPNESS', tone["sharpness_value"])
            s.setToneMapping(tone["gamma"], tone["burn"])
            s.setColorSpace(tone["color_space"])
            s.setWhitePoint(tone["whitepoint"], tone["tint"])
        
        if(materials is not None):
            if(materials["override"]):
                s.setOverrideMaterial(True)
            if(materials["override_path"] != ""):
                s.setOverrideMaterial(materials["override_path"])
            if(materials["search_path"] != ""):
                s.addSearchingPath(materials["search_path"])
        
        if(other is not None):
            if(other['protect']):
                s.enableProtection(True)
            else:
                s.enableProtection(False)
            
            if(other['extra_sampling_enabled']):
                s.setRenderParameter('DO EXTRA SAMPLING', 1)
                s.setRenderParameter('EXTRA SAMPLING SL', other['extra_sampling_sl'])
                s.setRenderParameter('EXTRA SAMPLING MASK', other['extra_sampling_mask'])
                if(platform.system() == 'Linux'):
                    # wtf?
                    s.setRenderParameter('EXTRA SAMPLING CUSTOM ALPHA', bytes(other['extra_sampling_custom_alpha'], encoding='UTF-8'))
                    s.setRenderParameter('EXTRA SAMPLING USER BITMAP', bytes(other['extra_sampling_user_bitmap'], encoding='UTF-8'))
                else:
                    s.setRenderParameter('EXTRA SAMPLING CUSTOM ALPHA', other['extra_sampling_custom_alpha'])
                    s.setRenderParameter('EXTRA SAMPLING USER BITMAP', other['extra_sampling_user_bitmap'])
                if(other['extra_sampling_invert']):
                    s.setRenderParameter('EXTRA SAMPLING INVERT', 1)
    
    def channels(self, base_path, mxi, image, image_depth='RGB8', channels_output_mode=0, channels_render=True, channels_render_type=0, channels=None, ):
        """Set scene render channels.
        base_path               string (path)
        mxi                     string (path)
        image                   string (path)
        image_depth             string              RGB8, RGB16, RGB32
        channels_output_mode    int
        channels_render         bool
        channels_render_type    int
        channels                dict     {channels_alpha                  bool
                                          channels_alpha_file             string
                                          channels_alpha_opaque           bool
                                          channels_custom_alpha           bool
                                          channels_custom_alpha_file      string
                                          channels_deep                   bool
                                          channels_deep_file              string
                                          channels_deep_max_samples       int
                                          channels_deep_min_dist          float
                                          channels_deep_type              int
                                          channels_fresnel                bool
                                          channels_fresnel_file           string
                                          channels_material_id            bool
                                          channels_material_id_file       string
                                          channels_motion_vector          bool
                                          channels_motion_vector_file     string
                                          channels_normals                bool
                                          channels_normals_file           string
                                          channels_normals_space          int
                                          channels_object_id              bool
                                          channels_object_id_file         string
                                          channels_position               bool
                                          channels_position_file          string
                                          channels_position_space         int
                                          channels_roughness              bool
                                          channels_roughness_file         string
                                          channels_shadow                 bool
                                          channels_shadow_file            string
                                          channels_uv                     bool
                                          channels_uv_file                string
                                          channels_z_buffer               bool
                                          channels_z_buffer_far           float
                                          channels_z_buffer_file          string
                                          channels_z_buffer_near          float} or None
        """
        def get_ext_depth(t, e=None):
            if(e is not None):
                t = "{}{}".format(e[1:].upper(), int(t[3:]))
            
            if(t == 'RGB8'):
                return ('.tif', 8)
            elif(t == 'RGB16'):
                return ('.tif', 16)
            elif(t == 'RGB32'):
                return ('.tif', 32)
            elif(t == 'PNG8'):
                return ('.png', 8)
            elif(t == 'PNG16'):
                return ('.png', 16)
            elif(t == 'TGA'):
                return ('.tga', 8)
            elif(t == 'TIF8'):
                return ('.tif', 8)
            elif(t == 'TIF16'):
                return ('.tif', 16)
            elif(t == 'TIF32'):
                return ('.tif', 32)
            elif(t == 'EXR16'):
                return ('.exr', 16)
            elif(t == 'EXR32'):
                return ('.exr', 32)
            elif(t == 'EXR_DEEP'):
                return ('.exr', 32)
            elif(t == 'JPG'):
                return ('.jpg', 8)
            elif(t == 'JP2'):
                return ('.jp2', 8)
            elif(t == 'HDR'):
                return ('.hdr', 32)
            elif(t == 'DTEX'):
                return ('.dtex', 32)
            elif(t == 'PSD8'):
                return ('.psd', 8)
            elif(t == 'PSD16'):
                return ('.psd', 16)
            elif(t == 'PSD32'):
                return ('.psd', 32)
            else:
                return ('.tif', 8)
        
        s = self.mxs
        
        s.setRenderParameter('DO NOT SAVE MXI FILE', (mxi is None))
        s.setRenderParameter('DO NOT SAVE IMAGE FILE', (image is None))
        if(mxi is not None):
            # s.setRenderParameter('MXI FULLNAME', mxi)
            # s.setRenderParameter('MXI FULLNAME', bytes(mxi, encoding='UTF-8'))
            if(platform.system() == 'Linux'):
                # wtf?
                s.setRenderParameter('MXI FULLNAME', bytes(mxi, encoding='UTF-8'))
            else:
                # s.setRenderParameter('MXI FULLNAME', mxi)
                s.setRenderParameter('MXI FULLNAME', bytes(mxi, encoding='UTF-8'))
        if(image is not None):
            if(image_depth is None):
                image_depth = 'RGB8'
            _, depth = get_ext_depth(image_depth, os.path.splitext(os.path.split(image)[1])[1])
            s.setPath('RENDER', image, depth)
        
        s.setRenderParameter('DO RENDER CHANNEL', int(channels_render))
        s.setRenderParameter('EMBED CHANNELS', channels_output_mode)
        
        s.setRenderParameter('RENDER LAYERS', channels_render_type)
        
        if(channels is not None):
            e, depth = get_ext_depth(channels["channels_alpha_file"])
            s.setPath('ALPHA', "{}_alpha{}".format(base_path, e), depth)
            e, depth = get_ext_depth(channels["channels_shadow_file"])
            s.setPath('SHADOW', "{}_shadow{}".format(base_path, e), depth)
            e, depth = get_ext_depth(channels["channels_object_id_file"])
            s.setPath('OBJECT', "{}_object_id{}".format(base_path, e), depth)
            e, depth = get_ext_depth(channels["channels_material_id_file"])
            s.setPath('MATERIAL', "{}_material_id{}".format(base_path, e), depth)
            e, depth = get_ext_depth(channels["channels_motion_vector_file"])
            s.setPath('MOTION', "{}_motion_vector{}".format(base_path, e), depth)
            e, depth = get_ext_depth(channels["channels_z_buffer_file"])
            s.setPath('Z', "{}_z_buffer{}".format(base_path, e), depth)
            e, depth = get_ext_depth(channels["channels_roughness_file"])
            s.setPath('ROUGHNESS', "{}_roughness{}".format(base_path, e), depth)
            e, depth = get_ext_depth(channels["channels_fresnel_file"])
            s.setPath('FRESNEL', "{}_fresnel{}".format(base_path, e), depth)
            e, depth = get_ext_depth(channels["channels_normals_file"])
            s.setPath('NORMALS', "{}_normals{}".format(base_path, e), depth)
            e, depth = get_ext_depth(channels["channels_position_file"])
            s.setPath('POSITION', "{}_position{}".format(base_path, e), depth)
            e, depth = get_ext_depth(channels["channels_deep_file"])
            s.setPath('DEEP', "{}_deep{}".format(base_path, e), depth)
            e, depth = get_ext_depth(channels["channels_uv_file"])
            s.setPath('UV', "{}_uv{}".format(base_path, e), depth)
            e, depth = get_ext_depth(channels["channels_custom_alpha_file"])
            s.setPath('ALPHA_CUSTOM', "{}_custom_alpha{}".format(base_path, e), depth)
            e, depth = get_ext_depth(channels["channels_reflectance_file"])
            s.setPath('REFLECTANCE', "{}_reflectance{}".format(base_path, e), depth)
            
            s.setRenderParameter('DO ALPHA CHANNEL', int(channels["channels_alpha"]))
            s.setRenderParameter('OPAQUE ALPHA', int(channels["channels_alpha_opaque"]))
            s.setRenderParameter('DO IDOBJECT CHANNEL', int(channels["channels_object_id"]))
            s.setRenderParameter('DO IDMATERIAL CHANNEL', int(channels["channels_material_id"]))
            s.setRenderParameter('DO SHADOW PASS CHANNEL', int(channels["channels_shadow"]))
            s.setRenderParameter('DO MOTION CHANNEL', int(channels["channels_motion_vector"]))
            s.setRenderParameter('DO ROUGHNESS CHANNEL', int(channels["channels_roughness"]))
            s.setRenderParameter('DO FRESNEL CHANNEL', int(channels["channels_fresnel"]))
            s.setRenderParameter('DO NORMALS CHANNEL', int(channels["channels_normals"]))
            s.setRenderParameter('NORMALS CHANNEL SPACE', channels["channels_normals_space"])
            s.setRenderParameter('POSITION CHANNEL SPACE', channels["channels_position_space"])
            s.setRenderParameter('DO POSITION CHANNEL', int(channels["channels_position"]))
            s.setRenderParameter('DO ZBUFFER CHANNEL', int(channels["channels_z_buffer"]))
            s.setRenderParameter('ZBUFFER RANGE', (channels["channels_z_buffer_near"], channels["channels_z_buffer_far"]))
            s.setRenderParameter('DO DEEP CHANNEL', int(channels["channels_deep"]))
            s.setRenderParameter('DEEP CHANNEL TYPE', channels["channels_deep_type"])
            s.setRenderParameter('DEEP MIN DISTANCE', channels["channels_deep_min_dist"])
            s.setRenderParameter('DEEP MAX SAMPLES', channels["channels_deep_max_samples"])
            s.setRenderParameter('DO UV CHANNEL', int(channels["channels_uv"]))
            # s.setRenderParameter('MOTION CHANNEL TYPE', ?)
            s.setRenderParameter('DO ALPHA CUSTOM CHANNEL', int(channels["channels_custom_alpha"]))
            s.setRenderParameter('DO REFLECTANCE CHANNEL', int(channels["channels_reflectance"]))
    
    def custom_alphas(self, groups, ):
        """Set custom alphas.
        groups      list of dicts: {'name': string, 'objects': list of strings, 'opaque': bool, }
        """
        s = self.mxs
        for a in groups:
            s.createCustomAlphaChannel(a['name'], a['opaque'])
            for n in a['objects']:
                o = s.getObject(n)
                o.addToCustomAlpha(a['name'])
    
    def ext_particles(self, name, properties, matrix, object_props=None, material=None, backface_material=None, ):
        """Create particles object.
        name                string
        properties          dict
        base                ((3 float), (3 float), (3 float), (3 float))
        pivot               ((3 float), (3 float), (3 float), (3 float))
        object_props        (bool hide, float opacity, tuple cid=(int, int, int), bool hcam, bool hcamsc, bool hgi, bool hrr, bool hzcp, ) or None
        material            (string path, bool embed) or None
        backface_material   (string path, bool embed) or None
        """
        s = self.mxs
        e = self.mgr.createDefaultGeometryProceduralExtension('MaxwellParticles')
        p = e.getExtensionData()
        d = properties
        
        if(d['embed'] is True):
            c = Cbase()
            c.origin = Cvector(0.0, 0.0, 0.0)
            c.xAxis = Cvector(1.0, 0.0, 0.0)
            c.yAxis = Cvector(0.0, 1.0, 0.0)
            c.zAxis = Cvector(0.0, 0.0, 1.0)
            p.setFloatArray('PARTICLE_POSITIONS', list(d['pdata']['PARTICLE_POSITIONS']), c)
            p.setFloatArray('PARTICLE_SPEEDS', list(d['pdata']['PARTICLE_SPEEDS']), c)
            p.setFloatArray('PARTICLE_RADII', list(d['pdata']['PARTICLE_RADII']), c)
            p.setIntArray('PARTICLE_IDS', list(d['pdata']['PARTICLE_IDS']))
            p.setFloatArray('PARTICLE_NORMALS', list(d['pdata']['PARTICLE_NORMALS']), c)
            p.setFloatArray('PARTICLE_UVW', list(d['pdata']['PARTICLE_UVW']), c)
        else:
            p.setString('FileName', d['filename'])
        
        p.setFloat('Radius Factor', d['radius_multiplier'])
        p.setFloat('MB Factor', d['motion_blur_multiplier'])
        p.setFloat('Shutter 1/', d['shutter_speed'])
        p.setFloat('Load particles %', d['load_particles'])
        p.setUInt('Axis', d['axis_system'])
        p.setInt('Frame#', d['frame_number'])
        p.setFloat('fps', d['fps'])
        p.setInt('Create N particles per particle', d['extra_create_np_pp'])
        p.setFloat('Extra particles dispersion', d['extra_dispersion'])
        p.setFloat('Extra particles deformation', d['extra_deformation'])
        p.setByte('Load particle Force', d['load_force'])
        p.setByte('Load particle Vorticity', d['load_vorticity'])
        p.setByte('Load particle Normal', d['load_normal'])
        p.setByte('Load particle neighbors no.', d['load_neighbors_num'])
        p.setByte('Load particle UV', d['load_uv'])
        p.setByte('Load particle Age', d['load_age'])
        p.setByte('Load particle Isolation Time', d['load_isolation_time'])
        p.setByte('Load particle Viscosity', d['load_viscosity'])
        p.setByte('Load particle Density', d['load_density'])
        p.setByte('Load particle Pressure', d['load_pressure'])
        p.setByte('Load particle Mass', d['load_mass'])
        p.setByte('Load particle Temperature', d['load_temperature'])
        p.setByte('Load particle ID', d['load_id'])
        p.setFloat('Min Force', d['min_force'])
        p.setFloat('Max Force', d['max_force'])
        p.setFloat('Min Vorticity', d['min_vorticity'])
        p.setFloat('Max Vorticity', d['max_vorticity'])
        p.setInt('Min Nneighbors', d['min_nneighbors'])
        p.setInt('Max Nneighbors', d['max_nneighbors'])
        p.setFloat('Min Age', d['min_age'])
        p.setFloat('Max Age', d['max_age'])
        p.setFloat('Min Isolation Time', d['min_isolation_time'])
        p.setFloat('Max Isolation Time', d['max_isolation_time'])
        p.setFloat('Min Viscosity', d['min_viscosity'])
        p.setFloat('Max Viscosity', d['max_viscosity'])
        p.setFloat('Min Density', d['min_density'])
        p.setFloat('Max Density', d['max_density'])
        p.setFloat('Min Pressure', d['min_pressure'])
        p.setFloat('Max Pressure', d['max_pressure'])
        p.setFloat('Min Mass', d['min_mass'])
        p.setFloat('Max Mass', d['max_mass'])
        p.setFloat('Min Temperature', d['min_temperature'])
        p.setFloat('Max Temperature', d['max_temperature'])
        p.setFloat('Min Velocity', d['min_velocity'])
        p.setFloat('Max Velocity', d['max_velocity'])
        
        o = s.createGeometryProceduralObject(name, p)
        
        a, _ = o.addChannelUVW()
        o.generateCustomUVW(0, a)
        
        self.set_base_and_pivot(o, matrix, )
        if(object_props is not None):
            self.set_object_props(o, *object_props)
        
        # if(material is not None):
        #     mat = self.load_material(*material)
        #     if(mat is not None):
        #         o.setMaterial(mat)
        # if(backface_material is not None):
        #     mat = self.load_material(*backface_material)
        #     if(mat is not None):
        #         o.setBackfaceMaterial(mat)
        
        if(material is not None):
            if(material != ''):
                mat = self.get_material(material)
                o.setMaterial(mat)
        if(backface_material is not None):
            if(backface_material != ''):
                mat = self.get_material(backface_material)
                o.setBackfaceMaterial(mat)
        
        return o
    
    def ext_hair(self, name, extension, matrix, root_radius, tip_radius, data, object_props=None, display_percent=10, display_max=1000, material=None, backface_material=None, ):
        """Create hair/grass object.
        name                string
        extension           string ('MaxwellHair' ,'MGrassP')
        base                ((3 float), (3 float), (3 float), (3 float))
        pivot               ((3 float), (3 float), (3 float), (3 float))
        root_radius         float
        tip_radius          float
        data                dict of extension data
        object_props        (bool hide, float opacity, tuple cid=(int, int, int), bool hcam, bool hcamsc, bool hgi, bool hrr, bool hzcp, ) or None
        display_percent     int
        display_max         int
        material            (string path, bool embed) or None
        backface_material   (string path, bool embed) or None
        """
        s = self.mxs
        e = self.mgr.createDefaultGeometryProceduralExtension(extension)
        p = e.getExtensionData()
        p.setByteArray('HAIR_MAJOR_VER', data['HAIR_MAJOR_VER'])
        p.setByteArray('HAIR_MINOR_VER', data['HAIR_MINOR_VER'])
        p.setByteArray('HAIR_FLAG_ROOT_UVS', data['HAIR_FLAG_ROOT_UVS'])
        
        m = memoryview(struct.pack("I", data['HAIR_GUIDES_COUNT'][0])).tolist()
        p.setByteArray('HAIR_GUIDES_COUNT', m)
        m = memoryview(struct.pack("I", data['HAIR_GUIDES_POINT_COUNT'][0])).tolist()
        p.setByteArray('HAIR_GUIDES_POINT_COUNT', m)
        
        c = Cbase()
        c.origin = Cvector(0.0, 0.0, 0.0)
        c.xAxis = Cvector(1.0, 0.0, 0.0)
        c.yAxis = Cvector(0.0, 1.0, 0.0)
        c.zAxis = Cvector(0.0, 0.0, 1.0)
        
        p.setFloatArray('HAIR_POINTS', list(data['HAIR_POINTS']), c)
        p.setFloatArray('HAIR_NORMALS', list(data['HAIR_NORMALS']), c)
        
        if(data['HAIR_FLAG_ROOT_UVS'][0] == 1):
            p.setFloatArray('HAIR_ROOT_UVS', list(data['HAIR_ROOT_UVS']), c)
        
        p.setUInt('Display Percent', display_percent)
        if(extension == 'MaxwellHair'):
            p.setUInt('Display Max. Hairs', display_max)
            p.setDouble('Root Radius', root_radius)
            p.setDouble('Tip Radius', tip_radius)
        if(extension == 'MGrassP'):
            p.setUInt('Display Max. Hairs', display_max)
            p.setDouble('Root Radius', root_radius)
            p.setDouble('Tip Radius', tip_radius)
        
        o = s.createGeometryProceduralObject(name, p)
        
        if(extension == 'MaxwellHair'):
            a, _ = o.addChannelUVW()
            o.generateCustomUVW(0, a)
            b, _ = o.addChannelUVW()
            o.generateCustomUVW(1, b)
            c, _ = o.addChannelUVW()
            o.generateCustomUVW(2, c)
        if(extension == 'MGrassP'):
            a, _ = o.addChannelUVW()
            o.generateCustomUVW(0, a)
            b, _ = o.addChannelUVW()
            o.generateCustomUVW(1, b)
        
        self.set_base_and_pivot(o, matrix, )
        if(object_props is not None):
            self.set_object_props(o, *object_props)
        
        # if(material is not None):
        #     mat = self.load_material(*material)
        #     if(mat is not None):
        #         o.setMaterial(mat)
        # if(backface_material is not None):
        #     mat = self.load_material(*backface_material)
        #     if(mat is not None):
        #         o.setBackfaceMaterial(mat)
        
        if(material is not None):
            if(material != ''):
                mat = self.get_material(material)
                o.setMaterial(mat)
        if(backface_material is not None):
            if(backface_material != ''):
                mat = self.get_material(backface_material)
                o.setBackfaceMaterial(mat)
        
        return o
    
    def ext_sea(self, name, matrix, object_props=None, geometry=None, wind=None, material=None, backface_material=None, ):
        """Create sea extension object.
        name                string
        base                ((3 float), (3 float), (3 float), (3 float))
        pivot               ((3 float), (3 float), (3 float), (3 float))
        object_props        (bool hide, float opacity, tuple cid=(int, int, int), bool hcam, bool hcamsc, bool hgi, bool hrr, bool hzcp, ) or None
        geometry            (float reference_time,
                             int resolution,
                             float ocean_depth,
                             float vertical_scale,
                             float ocean_dim,
                             int ocean_seed,
                             bool enable_choppyness,
                             float choppy_factor, )
        wind                (float ocean_wind_mod,
                             float ocean_wind_dir,
                             float ocean_wind_alignment,
                             float ocean_min_wave_length,
                             float damp_factor_against_wind, )
        material            (string path, bool embed) or None
        backface_material   (string path, bool embed) or None
        """
        s = self.mxs
        e = self.mgr.createDefaultGeometryLoaderExtension('MaxwellSea')
        p = e.getExtensionData()
        
        p.setFloat('Reference Time', geometry[0])
        p.setUInt('Resolution', geometry[1])
        p.setFloat('Ocean Depth', geometry[2])
        p.setFloat('Vertical Scale', geometry[3])
        p.setFloat('Ocean Dim', geometry[4])
        p.setUInt('Ocean Seed', geometry[5])
        p.setByte('Enable Choppyness', geometry[6])
        p.setFloat('Choppy factor', geometry[7])
        p.setByte('Enable White Caps', geometry[8])
        
        p.setFloat('Ocean Wind Mod.', wind[0])
        p.setFloat('Ocean Wind Dir.', wind[1])
        p.setFloat('Ocean Wind Alignment', wind[2])
        p.setFloat('Ocean Min. Wave Length', wind[3])
        p.setFloat('Damp Factor Against Wind', wind[4])
        
        o = s.createGeometryLoaderObject(name, p)
        
        self.set_base_and_pivot(o, matrix, )
        if(object_props is not None):
            self.set_object_props(o, *object_props)
        
        # if(material is not None):
        #     mat = self.load_material(*material)
        #     if(mat is not None):
        #         o.setMaterial(mat)
        # if(backface_material is not None):
        #     mat = self.load_material(*backface_material)
        #     if(mat is not None):
        #         o.setBackfaceMaterial(mat)
        
        if(material is not None):
            if(material != ''):
                mat = self.get_material(material)
                o.setMaterial(mat)
        if(backface_material is not None):
            if(backface_material != ''):
                mat = self.get_material(backface_material)
                o.setBackfaceMaterial(mat)
    
    def ext_volumetrics(self, name, properties, matrix, object_props=None, material=None, backface_material=None, ):
        """Create Volumetrics Extension Object.
        name                string
        properties          (int type 1, float density) or (int type 2, float density, int seed, float low, float high, float detail, int octaves, float perssistence)
        base                ((3 float), (3 float), (3 float), (3 float))
        pivot               ((3 float), (3 float), (3 float), (3 float))
        object_props        (bool hide, float opacity, tuple cid=(int, int, int), bool hcam, bool hcamsc, bool hgi, bool hrr, bool hzcp, ) or None
        material            (string path, bool embed) or None
        backface_material   (string path, bool embed) or None
        """
        s = self.mxs
        e = self.mgr.createDefaultGeometryProceduralExtension('MaxwellVolumetric')
        p = e.getExtensionData()
        d = properties
        
        p.setByte('Create Constant Density', d[0])
        p.setFloat('ConstantDensity', d[1])
        if(d[0] == 2):
            p.setUInt('Seed', d[2])
            p.setFloat('Low value', d[3])
            p.setFloat('High value', d[4])
            p.setFloat('Detail', d[5])
            p.setInt('Octaves', d[6])
            p.setFloat('Persistance', d[7])
        
        o = s.createGeometryProceduralObject(name, p)
        
        self.set_base_and_pivot(o, matrix, )
        if(object_props is not None):
            self.set_object_props(o, *object_props)
        
        # if(material is not None):
        #     mat = self.load_material(*material)
        #     if(mat is not None):
        #         o.setMaterial(mat)
        # if(backface_material is not None):
        #     mat = self.load_material(*backface_material)
        #     if(mat is not None):
        #         o.setBackfaceMaterial(mat)
        
        if(material is not None):
            if(material != ''):
                mat = self.get_material(material)
                o.setMaterial(mat)
        if(backface_material is not None):
            if(backface_material != ''):
                mat = self.get_material(backface_material)
                o.setBackfaceMaterial(mat)
        
        return o
    
    def mod_grass(self, object_name, properties, material=None, backface_material=None, ):
        """Create grass object modifier extension.
        object_name         string
        properties          dict of many, many properties, see code..
        material            (string path, bool embed) or None
        backface_material   (string path, bool embed) or None
        """
        s = self.mxs
        e = self.mgr.createDefaultGeometryModifierExtension('MaxwellGrass')
        p = e.getExtensionData()
        
        if(material is not None):
            mat = self.get_material(material)
            if(mat is not None):
                p.setString('Material', mat.getName())
        if(backface_material is not None):
            mat = self.get_material(backface_material)
            if(mat is not None):
                p.setString('Double Sided Material', mat.getName())
        
        p.setUInt('Density', properties['density'])
        self.texture_data_to_mxparams('Density Map', properties['density_map'], p, )
        
        p.setFloat('Length', properties['length'])
        self.texture_data_to_mxparams('Length Map', properties['length_map'], p, )
        p.setFloat('Length Variation', properties['length_variation'])
        
        p.setFloat('Root Width', properties['root_width'])
        p.setFloat('Tip Width', properties['tip_width'])
        
        p.setFloat('Direction Type', properties['direction_type'])
        
        p.setFloat('Initial Angle', properties['initial_angle'])
        p.setFloat('Initial Angle Variation', properties['initial_angle_variation'])
        self.texture_data_to_mxparams('Initial Angle Map', properties['initial_angle_map'], p, )
        
        p.setFloat('Start Bend', properties['start_bend'])
        p.setFloat('Start Bend Variation', properties['start_bend_variation'])
        self.texture_data_to_mxparams('Start Bend Map', properties['start_bend_map'], p, )
        
        p.setFloat('Bend Radius', properties['bend_radius'])
        p.setFloat('Bend Radius Variation', properties['bend_radius_variation'])
        self.texture_data_to_mxparams('Bend Radius Map', properties['bend_radius_map'], p, )
        
        p.setFloat('Bend Angle', properties['bend_angle'])
        p.setFloat('Bend Angle Variation', properties['bend_angle_variation'])
        self.texture_data_to_mxparams('Bend Angle Map', properties['bend_angle_map'], p, )
        
        p.setFloat('Cut Off', properties['cut_off'])
        p.setFloat('Cut Off Variation', properties['cut_off_variation'])
        self.texture_data_to_mxparams('Cut Off Map', properties['cut_off_map'], p, )
        
        p.setUInt('Points per Blade', properties['points_per_blade'])
        p.setUInt('Primitive Type', properties['primitive_type'])
        
        p.setUInt('Seed', properties['seed'])
        
        p.setByte('Enable LOD', properties['lod'])
        p.setFloat('LOD Min Distance', properties['lod_min_distance'])
        p.setFloat('LOD Max Distance', properties['lod_max_distance'])
        p.setFloat('LOD Max Distance Density', properties['lod_max_distance_density'])
        
        p.setUInt('Display Percent', properties['display_percent'])
        p.setUInt('Display Max. Blades', properties['display_max_blades'])
        
        o = s.getObject(object_name)
        o.applyGeometryModifierExtension(p)
        return o
    
    def mod_subdivision(self, object_name, level=2, scheme=0, interpolation=2, crease=0.0, smooth_angle=90.0, quads=None, ):
        """Create subdivision object modifier extension.
        object_name     string
        level           int
        scheme          int     (0, "Catmull-Clark"), (1, "Loop")
        interpolation   int     (0, "None"), (1, "Edges"), (2, "Edges And Corners"), (3, "Sharp")
        crease          float
        smooth          float
        quads           [[int, int], ...] or None
        """
        s = self.mxs
        e = self.mgr.createDefaultGeometryModifierExtension('SubdivisionModifier')
        p = e.getExtensionData()
        
        p.setUInt('Subdivision Level', level)
        p.setUInt('Subdivision Scheme', scheme)
        p.setUInt('Interpolation', interpolation)
        p.setFloat('Crease', crease)
        p.setFloat('Smooth Angle', smooth_angle)
        
        o = s.getObject(object_name)
        
        if(scheme == 0 and quads is not None):
            for t, q in quads:
                o.setTriangleQuadBuddy(t, q)
        
        o.applyGeometryModifierExtension(p)
        return o
    
    def mod_scatter(self, object_name, scatter_object, inherit_objectid=False, remove_overlapped=False, density=None, seed=0, scale=None, rotation=None, lod=None, angle=None, display_percent=10, display_max=1000, ):
        """Create scatter object modifier extension.
        object_name                 string
        scatter_object              string
        inherit_objectid            bool
        density                     (float, density_map or None) or None
        seed                        int
        scale                       ((float, float, float), scale_map or None, scale_variation (float, float, float)) or None
        rotation                    ((float, float, float), rotation_map or None, rotation_variation (float, float, float), rotation_direction int (0, "Polygon Normal"), (1, "World Z")) or None
        lod                         (bool, lod_min_distance float, lod_max_distance float, lod_max_distance_density float) or None
        display_percent             int
        display_max                 int
        """
        s = self.mxs
        e = self.mgr.createDefaultGeometryModifierExtension('MaxwellScatter')
        p = e.getExtensionData()
        
        p.setString('Object', scatter_object)
        p.setByte('Inherit ObjectID', inherit_objectid)
        if(density is not None):
            p.setFloat('Density', density[0])
            self.texture_data_to_mxparams('Density Map', density[1], p, )
        p.setUInt('Seed', seed)
        p.setByte('Remove Overlapped', remove_overlapped)
        
        if(scale is not None):
            p.setFloat('Scale X', scale[0])
            p.setFloat('Scale Y', scale[1])
            p.setFloat('Scale Z', scale[2])
            self.texture_data_to_mxparams('Scale Map', scale[3], p, )
            p.setFloat('Scale X Variation', scale[4])
            p.setFloat('Scale Y Variation', scale[5])
            p.setFloat('Scale Z Variation', scale[6])
            p.setByte('Uniform Scale', scale[7])
        if(rotation is not None):
            p.setFloat('Rotation X', rotation[0])
            p.setFloat('Rotation Y', rotation[1])
            p.setFloat('Rotation Z', rotation[2])
            self.texture_data_to_mxparams('Rotation Map', rotation[3], p, )
            p.setFloat('Rotation X Variation', rotation[4])
            p.setFloat('Rotation Y Variation', rotation[5])
            p.setFloat('Rotation Z Variation', rotation[6])
            p.setUInt('Direction Type', rotation[7])
        if(lod is not None):
            p.setByte('Enable LOD', lod[0])
            p.setFloat('LOD Min Distance', lod[1])
            p.setFloat('LOD Max Distance', lod[2])
            p.setFloat('LOD Max Distance Density', lod[3])
        if(angle is not None):
            p.setFloat('Direction Type', angle[0])
            p.setFloat('Initial Angle', angle[1])
            p.setFloat('Initial Angle Variation', angle[2])
            self.texture_data_to_mxparams('Initial Angle Map', angle[3], p, )
            
        p.setUInt('Display Percent', display_percent)
        p.setUInt('Display Max. Blades', display_max)
        
        o = s.getObject(object_name)
        o.applyGeometryModifierExtension(p)
        return o
    
    def mod_cloner(self, object_name, cloned_object, render_emitter, pdata, radius=1.0, mb_factor=1.0, load_percent=100.0, start_offset=0, ex_npp=0, ex_p_dispersion=0.0, ex_p_deformation=0.0, align_to_velocity=False, scale_with_radius=False, inherit_obj_id=False, frame=1, fps=24.0, display_percent=10, display_max=1000, ):
        """Create cloner object modifier extension.
        object_name         string
        cloned_object       string
        render_emitter      bool
        pdata               string or dict
        radius              float
        mb_factor           float
        load_percent        float
        start_offset        int
        ex_npp              int
        ex_p_dispersion     float
        ex_p_deformation    float
        align_to_velocity   bool
        scale_with_radius   bool
        inherit_obj_id      bool
        frame               int
        fps                 float
        display_percent     int
        display_max         int
        """
        s = self.mxs
        e = self.mgr.createDefaultGeometryModifierExtension('MaxwellCloner')
        p = e.getExtensionData()
        
        if(type(pdata) is dict):
            c = Cbase()
            c.origin = Cvector(0.0, 0.0, 0.0)
            c.xAxis = Cvector(1.0, 0.0, 0.0)
            c.yAxis = Cvector(0.0, 1.0, 0.0)
            c.zAxis = Cvector(0.0, 0.0, 1.0)
            p.setFloatArray('PARTICLE_POSITIONS', list(pdata['PARTICLE_POSITIONS']), c)
            p.setFloatArray('PARTICLE_SPEEDS', list(pdata['PARTICLE_SPEEDS']), c)
            p.setFloatArray('PARTICLE_RADII', list(pdata['PARTICLE_RADII']), c)
            p.setIntArray('PARTICLE_IDS', list(pdata['PARTICLE_IDS']))
        else:
            p.setString('FileName', pdata)
        
        p.setFloat('Radius Factor', radius)
        
        p.setFloat('MB Factor', mb_factor)
        p.setFloat('Load particles %', load_percent)
        p.setUInt('Start offset', start_offset)
        
        p.setUInt('Create N particles per particle', ex_npp)
        p.setFloat('Extra particles dispersion', ex_p_dispersion)
        p.setFloat('Extra particles deformation', ex_p_deformation)
        
        p.setByte('Use velocity', align_to_velocity)
        p.setByte('Scale with particle radius', scale_with_radius)
        p.setByte('Inherit ObjectID', inherit_obj_id)
        
        p.setInt('Frame#', frame)
        p.setFloat('fps', fps)
        
        p.setUInt('Display Percent', display_percent)
        p.setUInt('Display Max. Particles', display_max)
        
        if(not render_emitter):
            o = s.getObject(object_name)
            o.setHide(True)
        
        # o = s.getObject(object_name)
        o = s.getObject(cloned_object)
        o.applyGeometryModifierExtension(p)
        return o
    
    def wireframe_override_object_materials(self, clay_mat_name, wire_base_name, ):
        s = self.mxs
        
        it = CmaxwellObjectIterator()
        o = it.first(scene)
        l = []
        while not o.isNull():
            name, _ = o.getName()
            l.append(name)
            o = it.next()
        
        for o in l:
            # do not set material to wire base
            if(o.getName()[0] != wire_base_name):
                if(o.isInstance()[0] == 1):
                    instanced = o.getInstanced()
                    # do not set material to wire base instances
                    if(instanced.getName()[0] != wire_base_name):
                        o.setMaterial(clay_mat_name)
                else:
                    o.setMaterial(clay_mat_name)
    
    def wireframe_zero_scale_base(self, wire_base_name):
        s = self.mxs
        o = s.getObject(wire_base_name)
        
        z = (0.0, 0.0, 0.0)
        b = Cbase()
        b.origin = Cvector(*z)
        b.xAxis = Cvector(*z)
        b.yAxis = Cvector(*z)
        b.zAxis = Cvector(*z)
        p = Cbase()
        p.origin = Cvector(*z)
        p.xAxis = Cvector(1.0, 0.0, 0.0)
        p.yAxis = Cvector(0.0, 1.0, 0.0)
        p.zAxis = Cvector(0.0, 0.0, 1.0)
        
        o.setBaseAndPivot(b, p)
        o.setScale(Cvector(0, 0, 0))


class MXMWriter():
    def __init__(self, path, data, ):
        """Create Extension MXM.
        path    string (path)
        data    dict
        """
        
        if(__name__ != "__main__"):
            if(platform.system() == 'Darwin'):
                raise ImportError("No pymaxwell for Mac OS X..")
        
        log(self.__class__.__name__, 1, LogStyles.MESSAGE, prefix="* ", )
        
        self.path = path
        self.mxs = Cmaxwell(mwcallback)
        
        self.mgr = CextensionManager.instance()
        self.mgr.loadAllExtensions()
        
        mat = self.material(data)
        if(mat is not None):
            log("writing to: {}".format(self.path), 2, prefix="* ", )
            mat.write(path)
            log("done.", 2, prefix="* ", )
        else:
            raise RuntimeError("Something unexpected happened..")
    
    def texture_data_to_mxparams(self, name, data, mxparams, ):
        """Create CtextureMap, fill with parameters and put into mxparams.
        name        string
        data        dict {'type':               string,
                          'path':               string,
                          'channel':            int,
                          'use_override_map':   bool,
                          'tile_method_type':   [bool, bool],
                          'tile_method_units':  int,
                          'repeat':             [float, float],
                          'mirror':             [bool, bool],
                          'offset':             [float, float],
                          'rotation':           float,
                          'invert':             bool,
                          'alpha_only':         bool,
                          'interpolation':      bool,
                          'brightness':         float,
                          'contrast':           float,
                          'saturation':         float,
                          'hue':                float,
                          'rgb_clamp':          [float, float], }
        mxparams    mxparams
        """
        d = data
        if(d is None):
            return
        
        # t = mxparams.getTextureMap(name)[0]
        t = CtextureMap()
        t.setPath(d['path'])
        v = Cvector2D()
        v.assign(*d['repeat'])
        t.scale = v
        v = Cvector2D()
        v.assign(*d['offset'])
        t.offset = v
        t.rotation = d['rotation']
        t.uvwChannelID = d['channel']
        t.uIsTiled = d['tile_method_type'][0]
        t.vIsTiled = d['tile_method_type'][1]
        t.uIsMirrored = d['mirror'][0]
        t.vIsMirrored = d['mirror'][1]
        t.invert = d['invert']
        # t.doGammaCorrection = 0
        t.useAbsoluteUnits = d['tile_method_units']
        # t.normalMappingFlipRed = 0
        # t.normalMappingFlipGreen = 0
        # t.normalMappingFullRangeBlue = 0
        t.useAlpha = d['alpha_only']
        t.typeInterpolation = d['interpolation']
        t.saturation = d['saturation'] / 100
        t.contrast = d['contrast'] / 100
        t.brightness = d['brightness'] / 100
        t.hue = d['hue'] / 180
        t.clampMin = d['rgb_clamp'][0] / 255
        t.clampMax = d['rgb_clamp'][1] / 255
        t.useGlobalMap = d['use_override_map']
        # t.cosA = 1.000000
        # t.sinA = 0.000000
        ok = mxparams.setTextureMap(name, t)
        return mxparams
    
    def texture(self, d, ):
        """Create CtextureMap from parameters
        d   dict
        """
        s = self.mxs
        
        t = CtextureMap()
        t.setPath(d['path'])
        
        t.uvwChannelID = d['channel']
        
        t.brightness = d['brightness'] / 100
        t.contrast = d['contrast'] / 100
        t.saturation = d['saturation'] / 100
        t.hue = d['hue'] / 180
        
        t.useGlobalMap = d['use_override_map']
        t.useAbsoluteUnits = d['tile_method_units']
        
        t.uIsTiled = d['tile_method_type'][0]
        t.vIsTiled = d['tile_method_type'][1]
        
        t.uIsMirrored = d['mirror'][0]
        t.vIsMirrored = d['mirror'][1]
        
        vec = Cvector2D()
        vec.assign(d['offset'][0], d['offset'][1])
        t.offset = vec
        t.rotation = d['rotation']
        t.invert = d['invert']
        t.useAlpha = d['alpha_only']
        if(d['interpolation']):
            t.typeInterpolation = 1
        else:
            t.typeInterpolation = 0
        t.clampMin = d['rgb_clamp'][0] / 255
        t.clampMax = d['rgb_clamp'][1] / 255
        
        vec = Cvector2D()
        vec.assign(d['repeat'][0], d['repeat'][1])
        t.scale = vec
        
        return t
    
    def material_placeholder(self, n=None, ):
        if(n is not None):
            # n = '{}_{}'.format(n, 'MATERIAL_PLACEHOLDER')
            pass
        else:
            n = 'MATERIAL_PLACEHOLDER'
        
        s = self.mxs
        m = s.createMaterial(n)
        l = m.addLayer()
        b = l.addBSDF()
        r = b.getReflectance()
        a = Cattribute()
        a.activeType = MAP_TYPE_BITMAP
        t = CtextureMap()
        mgr = CextensionManager.instance()
        mgr.loadAllExtensions()
        e = mgr.createDefaultTextureExtension('Checker')
        ch = e.getExtensionData()
        ch.setUInt('Number of elements U', 32)
        ch.setUInt('Number of elements V', 32)
        t.addProceduralTexture(ch)
        a.textureMap = t
        r.setAttribute('color', a)
        return m
    
    def material_default(self, n, ):
        s = self.mxs
        m = s.createMaterial(n)
        l = m.addLayer()
        b = l.addBSDF()
        return m
    
    def material_external(self, d, ):
        s = self.mxs
        p = d['path']
        t = s.readMaterial(p)
        t.setName(d['name'])
        m = s.addMaterial(t)
        if(not d['embed']):
            m.setReference(1, p)
        return m
    
    def material_custom(self, d, ):
        s = self.mxs
        
        m = s.createMaterial(d['name'])
        d = d['data']
        
        def global_props(d, m):
            # global properties
            if(d['override_map']):
                t = texture(d['override_map'], s, )
                if(t is not None):
                    m.setGlobalMap(t)
            
            if(d['bump']):
                a = Cattribute()
                a.activeType = MAP_TYPE_BITMAP
                t = texture(d['bump_map'], s, )
                if(t is not None):
                    a.textureMap = t
                a.value = d['bump_value']
                m.setAttribute('bump', a)
            
            m.setDispersion(d['dispersion'])
            m.setMatteShadow(d['shadow'])
            m.setMatte(d['matte'])
            m.setNestedPriority(d['priority'])
            
            c = Crgb()
            cc = [c / 255 for c in d['id']]
            c.assign(*cc)
            m.setColorID(c)
            
            if(d['active_display_map']):
                t = texture(d['active_display_map'], s, )
                m.setActiveDisplayMap(t)
        
        def displacement(d, m):
            if(not d['enabled']):
                return
            
            m.enableDisplacement(True)
            if(d['map'] is not None):
                t = texture(d['map'], s)
                m.setDisplacementMap(t)
            m.setDisplacementCommonParameters(d['type'], d['subdivision'], int(d['smoothing']), d['offset'], d['subdivision_method'], d['uv_interpolation'], )
            m.setHeightMapDisplacementParameters(d['height'], d['height_units'], d['adaptive'], )
            v = Cvector(*d['v3d_scale'])
            m.setVectorDisplacementParameters(v, d['v3d_transform'], d['v3d_rgb_mapping'], d['v3d_preset'], )
        
        def add_bsdf(d, l):
            b = l.addBSDF()
            b.setName(d['name'])
            
            bp = d['bsdf_props']
            # weight
            if(bp['weight_map_enabled']):
                # t = texture(bp['weight_map'], s, )
                # a = Cattribute()
                # a.textureMap = t
                a = Cattribute()
                a.activeType = MAP_TYPE_BITMAP
                t = texture(bp['weight_map'], s, )
                if(t is not None):
                    a.textureMap = t
                a.value = bp['weight']
            else:
                a = Cattribute()
                a.activeType = MAP_TYPE_VALUE
                a.value = bp['weight']
            b.setWeight(a)
            # enabled
            if(not bp['visible']):
                b.setState(False)
            # ior
            r = b.getReflectance()
            if(bp['ior'] == 1):
                # measured data
                r.setActiveIorMode(1)
                r.setComplexIor(bp['complex_ior'])
            else:
                if(bp['reflectance_0_map_enabled']):
                    # t = texture(bp['reflectance_0_map'], s, )
                    # a = Cattribute()
                    # a.textureMap = t
                    a = Cattribute()
                    a.activeType = MAP_TYPE_BITMAP
                    t = texture(bp['reflectance_0_map'], s, )
                    if(t is not None):
                        a.textureMap = t
                    # a.value = bp['weight']
                    a.rgb.assign(*bp['reflectance_0'])
                else:
                    a = Cattribute()
                    a.activeType = MAP_TYPE_RGB
                    a.rgb.assign(*bp['reflectance_0'])
                r.setAttribute('color', a)
                
                if(bp['reflectance_90_map_enabled']):
                    # # a = texture(bp['reflectance_90_map'], s, )
                    # t = texture(bp['reflectance_90_map'], s, )
                    # a = Cattribute()
                    # a.textureMap = t
                    a = Cattribute()
                    a.activeType = MAP_TYPE_BITMAP
                    t = texture(bp['reflectance_90_map'], s, )
                    if(t is not None):
                        a.textureMap = t
                    # a.value = bp['weight']
                    a.rgb.assign(*bp['reflectance_90'])
                else:
                    a = Cattribute()
                    a.activeType = MAP_TYPE_RGB
                    a.rgb.assign(*bp['reflectance_90'])
                r.setAttribute('color.tangential', a)
                
                if(bp['transmittance_map_enabled']):
                    # # a = texture(bp['transmittance_map'], s, )
                    # t = texture(bp['transmittance_map'], s, )
                    # a = Cattribute()
                    # a.textureMap = t
                    a = Cattribute()
                    a.activeType = MAP_TYPE_BITMAP
                    t = texture(bp['transmittance_map'], s, )
                    if(t is not None):
                        a.textureMap = t
                    # a.value = bp['weight']
                    a.rgb.assign(*bp['transmittance'])
                else:
                    a = Cattribute()
                    a.activeType = MAP_TYPE_RGB
                    a.rgb.assign(*bp['transmittance'])
                r.setAttribute('transmittance.color', a)
                
                r.setAbsorptionDistance(bp['attenuation_units'], bp['attenuation'])
                r.setIOR(bp['nd'], bp['abbe'])
                if(bp['force_fresnel']):
                    r.enableForceFresnel(True)
                r.setConductor(bp['k'])
                if(bp['r2_enabled']):
                    r.setFresnelCustom(bp['r2_falloff_angle'], bp['r2_influence'], True, )
            # surface
            if(bp['roughness_map_enabled']):
                # # a = texture(bp['roughness_map'], s, )
                # t = texture(bp['roughness_map'], s, )
                # a = Cattribute()
                # a.textureMap = t
                a = Cattribute()
                a.activeType = MAP_TYPE_BITMAP
                t = texture(bp['roughness_map'], s, )
                if(t is not None):
                    a.textureMap = t
                a.value = bp['roughness']
                # a.rgb.assign(*bp['transmittance'])
            else:
                a = Cattribute()
                a.activeType = MAP_TYPE_VALUE
                a.value = bp['roughness']
            b.setAttribute('roughness', a)
            
            if(bp['bump_map_enabled']):
                # # a = texture(bp['bump_map'], s, )
                # t = texture(bp['bump_map'], s, )
                # a = Cattribute()
                # a.textureMap = t
                a = Cattribute()
                a.activeType = MAP_TYPE_BITMAP
                t = texture(bp['bump_map'], s, )
                if(t is not None):
                    a.textureMap = t
                a.value = bp['bump']
                # a.rgb.assign(*bp['transmittance'])
            else:
                a = Cattribute()
                a.activeType = MAP_TYPE_VALUE
                a.value = bp['bump']
            b.setAttribute('bump', a)
            b.setNormalMapState(bp['bump_map_use_normal'])
            
            if(bp['anisotrophy_map_enabled']):
                # # a = texture(bp['anisotrophy_map'], s, )
                # t = texture(bp['anisotrophy_map'], s, )
                # a = Cattribute()
                # a.textureMap = t
                a = Cattribute()
                a.activeType = MAP_TYPE_BITMAP
                t = texture(bp['anisotrophy_map'], s, )
                if(t is not None):
                    a.textureMap = t
                a.value = bp['anisotrophy']
                # a.rgb.assign(*bp['transmittance'])
            else:
                a = Cattribute()
                a.activeType = MAP_TYPE_VALUE
                a.value = bp['anisotrophy']
            b.setAttribute('anisotrophy', a)
            
            if(bp['anisotrophy_angle_map_enabled']):
                # # a = texture(bp['anisotrophy_angle_map'], s, )
                # t = texture(bp['anisotrophy_angle_map'], s, )
                # a = Cattribute()
                # a.textureMap = t
                a = Cattribute()
                a.activeType = MAP_TYPE_BITMAP
                t = texture(bp['anisotrophy_angle_map'], s, )
                if(t is not None):
                    a.textureMap = t
                a.value = bp['anisotrophy_angle']
                # a.rgb.assign(*bp['transmittance'])
            else:
                a = Cattribute()
                a.activeType = MAP_TYPE_VALUE
                a.value = bp['anisotrophy_angle']
            b.setAttribute('angle', a)
            
            # subsurface
            a = Cattribute()
            a.activeType = MAP_TYPE_RGB
            a.rgb.assign(*bp['scattering'])
            r.setAttribute('scattering', a)
            r.setScatteringParameters(bp['coef'], bp['asymmetry'], bp['single_sided'])
            if(bp['single_sided']):
                if(bp['single_sided_map_enabled']):
                    # # a = texture(bp['single_sided_map'], s, )
                    # t = texture(bp['single_sided_map'], s, )
                    # a = Cattribute()
                    # a.textureMap = t
                    a = Cattribute()
                    a.activeType = MAP_TYPE_BITMAP
                    t = texture(bp['single_sided_map'], s, )
                    if(t is not None):
                        a.textureMap = t
                    a.value = bp['single_sided_value']
                    # a.rgb.assign(*bp['transmittance'])
                else:
                    a = Cattribute()
                    a.activeType = MAP_TYPE_VALUE
                    a.value = bp['single_sided_value']
                r.setScatteringThickness(a)
                r.setScatteringThicknessRange(bp['single_sided_min'], bp['single_sided_max'])
            
            # coating
            cp = d['coating']
            if(cp['enabled']):
                c = b.addCoating()
                
                if(cp['thickness_map_enabled']):
                    # # a = texture(cp['thickness_map'], s, )
                    # t = texture(cp['thickness_map'], s, )
                    # a = Cattribute()
                    # a.textureMap = t
                    a = Cattribute()
                    a.activeType = MAP_TYPE_BITMAP
                    t = texture(cp['thickness_map'], s, )
                    if(t is not None):
                        a.textureMap = t
                    a.value = cp['thickness']
                    # a.rgb.assign(*bp['transmittance'])
                else:
                    a = Cattribute()
                    a.activeType = MAP_TYPE_VALUE
                    a.value = cp['thickness']
                c.setThickness(a)
                c.setThicknessRange(cp['thickness_map_min'], cp['thickness_map_max'])
                
                r = c.getReflectance()
                if(cp['ior'] == 1):
                    # measured data
                    r.setActiveIorMode(1)
                    r.setComplexIor(cp['complex_ior'])
                else:
                    if(cp['reflectance_0_map_enabled']):
                        # # a = texture(cp['reflectance_0_map'], s, )
                        # t = texture(cp['reflectance_0_map'], s, )
                        # a = Cattribute()
                        # a.textureMap = t
                        a = Cattribute()
                        a.activeType = MAP_TYPE_BITMAP
                        t = texture(cp['reflectance_0_map'], s, )
                        if(t is not None):
                            a.textureMap = t
                        # a.value = bp['thickness']
                        a.rgb.assign(*cp['reflectance_0'])
                    else:
                        a = Cattribute()
                        a.activeType = MAP_TYPE_RGB
                        a.rgb.assign(*cp['reflectance_0'])
                    r.setAttribute('color', a)
                    
                    if(cp['reflectance_90_map_enabled']):
                        # # a = texture(cp['reflectance_90_map'], s, )
                        # t = texture(cp['reflectance_90_map'], s, )
                        # a = Cattribute()
                        # a.textureMap = t
                        a = Cattribute()
                        a.activeType = MAP_TYPE_BITMAP
                        t = texture(cp['reflectance_90_map'], s, )
                        if(t is not None):
                            a.textureMap = t
                        # a.value = bp['thickness']
                        a.rgb.assign(*cp['reflectance_90'])
                    else:
                        a = Cattribute()
                        a.activeType = MAP_TYPE_RGB
                        a.rgb.assign(*cp['reflectance_90'])
                    r.setAttribute('color.tangential', a)
                    r.setIOR(cp['nd'], 1.0, )
                    if(cp['force_fresnel']):
                        r.enableForceFresnel(True)
                    r.setConductor(cp['k'])
                    if(cp['r2_enabled']):
                        r.setFresnelCustom(cp['r2_falloff_angle'], 0.0, True, )
        
        def add_emitter(d, l):
            e = l.createEmitter()
            
            if(d['type'] == 0):
                e.setLobeType(EMISSION_LOBE_DEFAULT)
            elif(d['type'] == 1):
                e.setLobeType(EMISSION_LOBE_IES)
                e.setLobeIES(d['ies_data'])
                e.setIESLobeIntensity(d['ies_intensity'])
            elif(d['type'] == 2):
                e.setLobeType(EMISSION_LOBE_SPOTLIGHT)
                if(d['spot_map'] is not None):
                    t = texture(d['spot_map'], s)
                    if(t is not None):
                        e.setLobeImageProjectedMap(d['spot_map_enabled'], t)
                e.setSpotConeAngle(d['spot_cone_angle'])
                e.setSpotFallOffAngle(d['spot_falloff_angle'])
                e.setSpotFallOffType(d['spot_falloff_type'])
                e.setSpotBlur(d['spot_blur'])
            if(d['emission'] == 0):
                e.setActiveEmissionType(EMISSION_TYPE_PAIR)
                ep = CemitterPair()
                # c = Crgb8()
                c = Crgb()
                c.assign(*d['color'])
                # ep.rgb.assign(c.toRGB())
                ep.rgb.assign(c)
                ep.temperature = d['color_black_body']
                ep.watts = d['luminance_power']
                ep.luminousEfficacy = d['luminance_efficacy']
                ep.luminousPower = d['luminance_output']
                ep.illuminance = d['luminance_output']
                ep.luminousIntensity = d['luminance_output']
                ep.luminance = d['luminance_output']
                e.setPair(ep)
                
                if(d['luminance'] == 0):
                    u = EMISSION_UNITS_WATTS_AND_LUMINOUS_EFFICACY
                elif(d['luminance'] == 1):
                    u = EMISSION_UNITS_LUMINOUS_POWER
                elif(d['luminance'] == 2):
                    u = EMISSION_UNITS_ILLUMINANCE
                elif(d['luminance'] == 3):
                    u = EMISSION_UNITS_LUMINOUS_INTENSITY
                elif(d['luminance'] == 4):
                    u = EMISSION_UNITS_LUMINANCE
                if(d['color_black_body_enabled']):
                    e.setActivePair(EMISSION_COLOR_TEMPERATURE, u)
                else:
                    e.setActivePair(EMISSION_RGB, u)
            
            elif(d['emission'] == 1):
                e.setActiveEmissionType(EMISSION_TYPE_TEMPERATURE)
                e.setTemperature(d['temperature_value'])
            elif(d['emission'] == 2):
                e.setActiveEmissionType(EMISSION_TYPE_MXI)
                a = Cattribute()
                a.activeType = MAP_TYPE_BITMAP
                t = texture(d['hdr_map'], s)
                if(t is not None):
                    a.textureMap = t
                a.value = d['hdr_intensity']
                e.setMXI(a)
            
            e.setState(True)
        
        def add_layer(d, m):
            l = m.addLayer()
            l.setName(d['name'])
            
            lpd = d['layer_props']
            if(not lpd['visible']):
                l.setEnabled(False)
            if(lpd['blending'] == 1):
                l.setStackedBlendingMode(1)
            if(lpd['opacity_map_enabled']):
                # a = texture(lpd['opacity_map'], s, )
                a = Cattribute()
                a.activeType = MAP_TYPE_BITMAP
                t = texture(lpd['opacity_map'], s, )
                if(t is not None):
                    a.textureMap = t
                a.value = lpd['opacity']
            else:
                a = Cattribute()
                a.activeType = MAP_TYPE_VALUE
                a.value = lpd['opacity']
            l.setAttribute('weight', a)
            
            epd = d['emitter']
            if(epd['enabled']):
                add_emitter(epd, l)
        
            for b in d['bsdfs']:
                add_bsdf(b, l)
        
        global_props(d['global_props'], m)
        displacement(d['displacement'], m)
        for layer in d['layers']:
            add_layer(layer, m)
        
        return m
    
    def material(self, d, ):
        s = self.mxs
        if(d['subtype'] == 'EXTERNAL'):
            if(d['path'] == ''):
                m = self.material_placeholder(d['name'])
            else:
                m = self.material_external(d)
                
                if(d['override']):
                    # global properties
                    if(d['override_map']):
                        t = self.texture(d['override_map'])
                        if(t is not None):
                            m.setGlobalMap(t)
                    
                    if(d['bump']):
                        a = Cattribute()
                        a.activeType = MAP_TYPE_BITMAP
                        t = self.texture(d['bump_map'])
                        if(t is not None):
                            a.textureMap = t
                        a.value = d['bump_value']
                        m.setAttribute('bump', a)
                    
                    m.setDispersion(d['dispersion'])
                    m.setMatteShadow(d['shadow'])
                    m.setMatte(d['matte'])
                    m.setNestedPriority(d['priority'])
                    
                    c = Crgb()
                    cc = [c / 255 for c in d['id']]
                    c.assign(*cc)
                    m.setColorID(c)
        
        elif(d['subtype'] == 'EXTENSION'):
            if(d['use'] == 'EMITTER'):
                m = s.createMaterial(d['name'])
                l = m.addLayer()
                e = l.createEmitter()
                
                if(d['emitter_type'] == 0):
                    e.setLobeType(EMISSION_LOBE_DEFAULT)
                elif(d['emitter_type'] == 1):
                    e.setLobeType(EMISSION_LOBE_IES)
                    e.setLobeIES(d['emitter_ies_data'])
                    e.setIESLobeIntensity(d['emitter_ies_intensity'])
                elif(d['emitter_type'] == 2):
                    # e.setLobeType(EMISSION_LOBE_BITMAP)
                    e.setLobeType(EMISSION_LOBE_SPOTLIGHT)
                    if(d['emitter_spot_map'] is not None):
                        t = self.texture(d['emitter_spot_map'])
                        if(t is not None):
                            e.setLobeImageProjectedMap(d['emitter_spot_map_enabled'], t)
                    e.setSpotConeAngle(d['emitter_spot_cone_angle'])
                    e.setSpotFallOffAngle(d['emitter_spot_falloff_angle'])
                    e.setSpotFallOffType(d['emitter_spot_falloff_type'])
                    e.setSpotBlur(d['emitter_spot_blur'])
                
                if(d['emitter_emission'] == 0):
                    e.setActiveEmissionType(EMISSION_TYPE_PAIR)
                    
                    ep = CemitterPair()
                    c = Crgb8()
                    c.assign(*d['emitter_color'])
                    ep.rgb.assign(c.toRGB())
                    ep.temperature = d['emitter_color_black_body']
                    ep.watts = d['emitter_luminance_power']
                    ep.luminousEfficacy = d['emitter_luminance_efficacy']
                    ep.luminousPower = d['emitter_luminance_output']
                    ep.illuminance = d['emitter_luminance_output']
                    ep.luminousIntensity = d['emitter_luminance_output']
                    ep.luminance = d['emitter_luminance_output']
                    e.setPair(ep)
                    
                    if(d['emitter_color_black_body_enabled']):
                        e.setActivePair(EMISSION_COLOR_TEMPERATURE)
                    else:
                        if(d['emitter_luminance'] == 0):
                            u = EMISSION_UNITS_WATTS_AND_LUMINOUS_EFFICACY
                        elif(d['emitter_luminance'] == 1):
                            u = EMISSION_UNITS_LUMINOUS_POWER
                        elif(d['emitter_luminance'] == 2):
                            u = EMISSION_UNITS_ILLUMINANCE
                        elif(d['emitter_luminance'] == 3):
                            u = EMISSION_UNITS_LUMINOUS_INTENSITY
                        elif(d['emitter_luminance'] == 4):
                            u = EMISSION_UNITS_LUMINANCE
                        e.setActivePair(EMISSION_RGB, u)
                
                elif(d['emitter_emission'] == 1):
                    e.setActiveEmissionType(EMISSION_TYPE_TEMPERATURE)
                    e.setTemperature(d['emitter_temperature_value'])
                elif(d['emitter_emission'] == 2):
                    e.setActiveEmissionType(EMISSION_TYPE_MXI)
                    a = Cattribute()
                    a.activeType = MAP_TYPE_BITMAP
                    t = self.texture(d['emitter_hdr_map'])
                    if(t is not None):
                        a.textureMap = t
                    a.value = d['emitter_hdr_intensity']
                    e.setMXI(a)
                
                e.setState(True)
            else:
                m = CextensionManager.instance()
                m.loadAllExtensions()
                if(d['use'] == 'AGS'):
                    e = m.createDefaultMaterialModifierExtension('AGS')
                    p = e.getExtensionData()
                    
                    c = Crgb8()
                    c.assign(*d['ags_color'])
                    p.setRgb('Color', c.toRGB())
                    p.setFloat('Reflection', d['ags_reflection'])
                    p.setUInt('Type', d['ags_type'])
                
                elif(d['use'] == 'OPAQUE'):
                    e = m.createDefaultMaterialModifierExtension('Opaque')
                    p = e.getExtensionData()
                    
                    p.setByte('Color Type', d['opaque_color_type'])
                    c = Crgb8()
                    c.assign(*d['opaque_color'])
                    p.setRgb('Color', c.toRGB())
                    self.texture_data_to_mxparams('Color Map', d['opaque_color_map'], p, )
                    
                    p.setByte('Shininess Type', d['opaque_shininess_type'])
                    p.setFloat('Shininess', d['opaque_shininess'])
                    self.texture_data_to_mxparams('Shininess Map', d['opaque_shininess_map'], p, )
                    
                    p.setByte('Roughness Type', d['opaque_roughness_type'])
                    p.setFloat('Roughness', d['opaque_roughness'])
                    self.texture_data_to_mxparams('Roughness Map', d['opaque_roughness_map'], p, )
                    
                    p.setByte('Clearcoat', d['opaque_clearcoat'])
                
                elif(d['use'] == 'TRANSPARENT'):
                    e = m.createDefaultMaterialModifierExtension('Transparent')
                    p = e.getExtensionData()
                    
                    p.setByte('Color Type', d['transparent_color_type'])
                    c = Crgb8()
                    c.assign(*d['transparent_color'])
                    p.setRgb('Color', c.toRGB())
                    self.texture_data_to_mxparams('Color Map', d['transparent_color_map'], p, )
                    
                    p.setFloat('Ior', d['transparent_ior'])
                    p.setFloat('Transparency', d['transparent_transparency'])
                    
                    p.setByte('Roughness Type', d['transparent_roughness_type'])
                    p.setFloat('Roughness', d['transparent_roughness'])
                    self.texture_data_to_mxparams('Roughness Map', d['transparent_roughness_map'], p, )
                    
                    p.setFloat('Specular Tint', d['transparent_specular_tint'])
                    p.setFloat('Dispersion', d['transparent_dispersion'])
                    p.setByte('Clearcoat', d['transparent_clearcoat'])
                
                elif(d['use'] == 'METAL'):
                    e = m.createDefaultMaterialModifierExtension('Metal')
                    p = e.getExtensionData()
                    
                    p.setUInt('IOR', d['metal_ior'])
                    
                    p.setFloat('Tint', d['metal_tint'])
                    
                    p.setByte('Color Type', d['metal_color_type'])
                    c = Crgb8()
                    c.assign(*d['metal_color'])
                    p.setRgb('Color', c.toRGB())
                    self.texture_data_to_mxparams('Color Map', d['metal_color_map'], p, )
                    
                    p.setByte('Roughness Type', d['metal_roughness_type'])
                    p.setFloat('Roughness', d['metal_roughness'])
                    self.texture_data_to_mxparams('Roughness Map', d['metal_roughness_map'], p, )
                    
                    p.setByte('Anisotropy Type', d['metal_anisotropy_type'])
                    p.setFloat('Anisotropy', d['metal_anisotropy'])
                    self.texture_data_to_mxparams('Anisotropy Map', d['metal_anisotropy_map'], p, )
                    
                    p.setByte('Angle Type', d['metal_angle_type'])
                    p.setFloat('Angle', d['metal_angle'])
                    self.texture_data_to_mxparams('Angle Map', d['metal_angle_map'], p, )
                    
                    p.setByte('Dust Type', d['metal_dust_type'])
                    p.setFloat('Dust', d['metal_dust'])
                    self.texture_data_to_mxparams('Dust Map', d['metal_dust_map'], p, )
                    
                    p.setByte('Perforation Enabled', d['metal_perforation_enabled'])
                    self.texture_data_to_mxparams('Perforation Map', d['metal_perforation_map'], p, )
                
                elif(d['use'] == 'TRANSLUCENT'):
                    e = m.createDefaultMaterialModifierExtension('Translucent')
                    p = e.getExtensionData()
                    
                    p.setFloat('Scale', d['translucent_scale'])
                    p.setFloat('Ior', d['translucent_ior'])
                    
                    p.setByte('Color Type', d['translucent_color_type'])
                    c = Crgb8()
                    c.assign(*d['translucent_color'])
                    p.setRgb('Color', c.toRGB())
                    self.texture_data_to_mxparams('Color Map', d['translucent_color_map'], p, )
                    
                    p.setFloat('Hue Shift', d['translucent_hue_shift'])
                    p.setByte('Invert Hue', d['translucent_invert_hue'])
                    p.setFloat('Vibrance', d['translucent_vibrance'])
                    p.setFloat('Density', d['translucent_density'])
                    p.setFloat('Opacity', d['translucent_opacity'])
                    
                    p.setByte('Roughness Type', d['translucent_roughness_type'])
                    p.setFloat('Roughness', d['translucent_roughness'])
                    self.texture_data_to_mxparams('Roughness Map', d['translucent_roughness_map'], p, )
                    
                    p.setFloat('Specular Tint', d['translucent_specular_tint'])
                    p.setByte('Clearcoat', d['translucent_clearcoat'])
                    p.setFloat('Clearcoat Ior', d['translucent_clearcoat_ior'])
                
                elif(d['use'] == 'CARPAINT'):
                    e = m.createDefaultMaterialModifierExtension('Car Paint')
                    p = e.getExtensionData()
                    
                    c = Crgb8()
                    c.assign(*d['carpaint_color'])
                    p.setRgb('Color', c.toRGB())
                    
                    p.setFloat('Metallic', d['carpaint_metallic'])
                    p.setFloat('Topcoat', d['carpaint_topcoat'])
                
                m = s.createMaterial(d['name'])
                m.applyMaterialModifierExtension(p)
                
                # global properties
                if(d['override_map']):
                    t = self.texture(d['override_map'])
                    if(t is not None):
                        m.setGlobalMap(t)
                
                if(d['bump']):
                    a = Cattribute()
                    a.activeType = MAP_TYPE_BITMAP
                    t = self.texture(d['bump_map'])
                    if(t is not None):
                        a.textureMap = t
                    a.value = d['bump_value']
                    m.setAttribute('bump', a)
                
                m.setDispersion(d['dispersion'])
                m.setMatteShadow(d['shadow'])
                m.setMatte(d['matte'])
                
                m.setNestedPriority(d['priority'])
                
                c = Crgb()
                cc = [c / 255 for c in d['id']]
                c.assign(*cc)
                m.setColorID(c)
        elif(d['subtype'] == 'CUSTOM'):
            m = self.material_custom(d)
        else:
            raise TypeError("Material '{}' {} is unknown type".format(d['name'], d['subtype']))
        return m
    
    def get_material(self, n, ):
        """get material by name from scene, if material is missing, create and return placeholder"""
        def get_material_names(s):
            it = CmaxwellMaterialIterator()
            o = it.first(s)
            l = []
            while not o.isNull():
                name = o.getName()
                l.append(name)
                o = it.next()
            return l
        
        s = self.mxs
        names = get_material_names(s)
        m = None
        if(n in names):
            m = s.getMaterial(n)
        if(m is None):
            # should not happen because i stopped changing material names.. but i leave it here
            m = self.material_placeholder()
        return m


class MXMEmitterCheck():
    def __init__(self, path, ):
        if(__name__ != "__main__"):
            if(platform.system() == 'Darwin'):
                raise ImportError("No pymaxwell for Mac OS X..")
        
        log(self.__class__.__name__, 1, LogStyles.MESSAGE, prefix="* ", )
        
        self.path = path
        self.mxs = Cmaxwell(mwcallback)
        self.emitter = False
        
        m = self.mxs.readMaterial(self.path)
        for i in range(m.getNumLayers()[0]):
            l = m.getLayer(i)
            e = l.getEmitter()
            if(e.isNull()):
                # no emitter layer
                self.emitter = False
                return
            if(not e.getState()[0]):
                # there is, but is disabled
                self.emitter = False
                return
            # is emitter
            self.emitter = True


class MXSReader():
    def __init__(self, path, ):
        if(__name__ != "__main__"):
            if(platform.system() == 'Darwin'):
                raise ImportError("No pymaxwell for Mac OS X..")
        
        log(self.__class__.__name__, 1, LogStyles.MESSAGE, prefix="* ", )
        
        self.path = path
        self.mxs = Cmaxwell(mwcallback)
        log("loading {}".format(self.path), 2, prefix="* ", )
        self.mxs.readMXS(self.path)
        if(self.mxs.isProtectionEnabled()):
            raise RuntimeError("Protected MXS")
        
        self._prepare()
    
    def _mxs_get_objects_names(self):
        s = self.mxs
        it = CmaxwellObjectIterator()
        o = it.first(s)
        l = []
        while not o.isNull():
            name, _ = o.getName()
            l.append(name)
            o = it.next()
        return l
    
    def _mxs_object(self, o):
        is_instance, _ = o.isInstance()
        is_mesh, _ = o.isMesh()
        if(is_instance == 0 and is_mesh == 0):
            log("only empties, meshes and instances are supported..", 2, LogStyles.WARNING, )
            return None
        r = {'name': o.getName()[0],
             'vertices': [],
             'normals': [],
             'triangles': [],
             'trianglesUVW': [],
             'matrix': (),
             'parent': None,
             'type': '',
             'materials': [],
             'nmats': 0,
             'matnames': [], }
        if(is_instance == 1):
            io = o.getInstanced()
            ion = io.getName()[0]
            b, p = self._base_and_pivot(o)
            r = {'name': o.getName()[0],
                 'base': b,
                 'pivot': p,
                 'parent': None,
                 'type': 'INSTANCE',
                 'instanced': ion, }
            # no multi material instances, always one material per instance
            m, _ = o.getMaterial()
            if(m.isNull() == 1):
                r['material'] = None
            else:
                r['material'] = o.getName()
            p, _ = o.getParent()
            if(not p.isNull()):
                r['parent'] = p.getName()[0]
        
            cid, _ = o.getColorID()
            rgb8 = cid.toRGB8()
            col = [str(rgb8.r()), str(rgb8.g()), str(rgb8.b())]
            r['colorid'] = ", ".join(col)
        
            h = []
            if(o.getHideToCamera()):
                h.append("C")
            if(o.getHideToGI()):
                h.append("GI")
            if(o.getHideToReflectionsRefractions()):
                h.append("RR")
            r['hidden'] = ", ".join(h)
        
            return r
        # counts
        nv, _ = o.getVerticesCount()
        nn, _ = o.getNormalsCount()
        nt, _ = o.getTrianglesCount()
        nppv, _ = o.getPositionsPerVertexCount()
        ppv = 0
        if(nv > 0):
            r['type'] = 'MESH'
        
            cid, _ = o.getColorID()
            rgb8 = cid.toRGB8()
            col = [str(rgb8.r()), str(rgb8.g()), str(rgb8.b())]
            r['colorid'] = ", ".join(col)
        
            h = []
            if(o.getHideToCamera()):
                h.append("C")
            if(o.getHideToGI()):
                h.append("GI")
            if(o.getHideToReflectionsRefractions()):
                h.append("RR")
            r['hidden'] = ", ".join(h)
        
        else:
            r['type'] = 'EMPTY'
        
            cid, _ = o.getColorID()
            rgb8 = cid.toRGB8()
            col = [str(rgb8.r()), str(rgb8.g()), str(rgb8.b())]
            r['colorid'] = ", ".join(col)
        
        if(nppv - 1 != ppv and nv != 0):
            log("only one position per vertex is supported..", 2, LogStyles.WARNING, )
        # vertices
        for i in range(nv):
            v, _ = o.getVertex(i, ppv)
            # (float x, float y, float z)
            r['vertices'].append((v.x(), v.y(), v.z()))
        # normals
        for i in range(nn):
            v, _ = o.getNormal(i, ppv)
            # (float x, float y, float z)
            r['normals'].append((v.x(), v.y(), v.z()))
        # triangles
        for i in range(nt):
            t = o.getTriangle(i)
            # (int v1, int v2, int v3, int n1, int n2, int n3)
            r['triangles'].append(t)
        # materials
        mats = []
        for i in range(nt):
            m, _ = o.getTriangleMaterial(i)
            if(m.isNull() == 1):
                n = None
            else:
                n = m.getName()
            if(n not in mats):
                mats.append(n)
            r['materials'].append((i, n))
        r['nmats'] = len(mats)
        r['matnames'] = mats
        # uv channels
        ncuv, _ = o.getChannelsUVWCount()
        for cuv in range(ncuv):
            # uv triangles
            r['trianglesUVW'].append([])
            for i in range(nt):
                t = o.getTriangleUVW(i, cuv)
                # float u1, float v1, float w1, float u2, float v2, float w2, float u3, float v3, float w3
                r['trianglesUVW'][cuv].append(t)
        # base and pivot to matrix
        b, p = self._base_and_pivot(o)
        r['base'] = b
        r['pivot'] = p
        # parent
        p, _ = o.getParent()
        if(not p.isNull()):
            r['parent'] = p.getName()[0]
        return r
    
    def _mxs_camera(self, c):
        v = c.getValues()
        s = c.getStep(0)
        o = s[0]
        f = s[1]
        u = s[2]
        r = {'name': v['name'],
             'shutter': 1.0 / v['shutter'],
             'iso': v['iso'],
             'x_res': v['xRes'],
             'y_res': v['yRes'],
             'pixel_aspect': v['pixelAspect'],
             'origin': (o.x(), o.y(), o.z()),
             'focal_point': (f.x(), f.y(), f.z()),
             'up': (u.x(), u.y(), u.z()),
             'focal_length': self._uncorrect_focal_length(s) * 1000.0,
             'f_stop': s[4],
             'film_width': round(v['filmWidth'] * 1000.0, 3),
             'film_height': round(v['filmHeight'] * 1000.0, 3),
             'active': False,
             'sensor_fit': None,
             'shift_x': 0.0,
             'shift_y': 0.0,
             'zclip': False,
             'zclip_near': 0.0,
             'zclip_far': 1000000.0,
             'type': 'CAMERA', }
        if(r['film_width'] > r['film_height']):
            r['sensor_fit'] = 'HORIZONTAL'
        else:
            r['sensor_fit'] = 'VERTICAL'
        cp = c.getCutPlanes()
        if(cp[2] is True):
            r['zclip'] = True
            r['zclip_near'] = cp[0]
            r['zclip_far'] = cp[1]
        sl = c.getShiftLens()
        r['shift_x'] = sl[0]
        r['shift_y'] = sl[1]
        d = c.getDiaphragm()
        r['diaphragm_type'] = d[0][0]
        r['diaphragm_angle'] = d[1]
        r['diaphragm_blades'] = d[2]
        return r
    
    def _base_and_pivot(self, o):
        b, p, _ = o.getBaseAndPivot()
        o = b.origin
        x = b.xAxis
        y = b.yAxis
        z = b.zAxis
        rb = [[o.x(), o.y(), o.z()], [x.x(), x.y(), x.z()], [y.x(), y.y(), y.z()], [z.x(), z.y(), z.z()]]
        rp = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0), )
        return rb, rp
    
    def _uncorrect_focal_length(self, step):
        flc = step[3]
        o = step[0]
        fp = step[1]
        d = Cvector()
        d.substract(fp, o)
        fd = d.norm()
        fluc = 1.0 / (1.0 / flc - 1 / fd)
        return fluc
    
    def _prepare(self):
        s = self.mxs
        self.object_names = self._mxs_get_objects_names()
    
    def _is_emitter(self, o):
        is_instance, _ = o.isInstance()
        is_mesh, _ = o.isMesh()
        if(not is_mesh and not is_instance):
            return False
        if(is_mesh):
            nt, _ = o.getTrianglesCount()
            mats = []
            for i in range(nt):
                m, _ = o.getTriangleMaterial(i)
                if(not m.isNull()):
                    if(m not in mats):
                        mats.append(m)
            for m in mats:
                nl, _ = m.getNumLayers()
                for i in range(nl):
                    l = m.getLayer(i)
                    e = l.getEmitter()
                    if(not e.isNull()):
                        return True
        if(is_instance):
            m, _ = o.getMaterial()
            if(not m.isNull()):
                nl, _ = m.getNumLayers()
                for i in range(nl):
                    l = m.getLayer(i)
                    e = l.getEmitter()
                    if(not e.isNull()):
                        return True
        return False
    
    def _global_transform(self, o):
        cb, _ = o.getWorldTransform()
        o = cb.origin
        x = cb.xAxis
        y = cb.yAxis
        z = cb.zAxis
        rb = [[o.x(), o.y(), o.z()], [x.x(), x.y(), x.z()], [y.x(), y.y(), y.z()], [z.x(), z.y(), z.z()]]
        rp = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0), )
        return rb, rp
    
    def objects(self, only_emitters=False):
        if(only_emitters):
            s = self.mxs
            data = []
            log("converting emitters..", 2)
            for n in self.object_names:
                d = None
                o = s.getObject(n)
                if(self._is_emitter(o)):
                    d = self._mxs_object(o)
                    if(d is not None):
                        b, p = self._global_transform(o)
                        d['base'] = b
                        d['pivot'] = p
                        d['parent'] = None
                        data.append(d)
        else:
            s = self.mxs
            data = []
            log("converting empties, meshes and instances..", 2)
            for n in self.object_names:
                d = None
                o = s.getObject(n)
                d = self._mxs_object(o)
                if(d is not None):
                    data.append(d)
        return data
    
    def cameras(self):
        s = self.mxs
        data = []
        log("converting cameras..", 2)
        nms = s.getCameraNames()
        cams = []
        if(type(nms) == list):
            for n in nms:
                cams.append(s.getCamera(n))
        for c in cams:
            d = self._mxs_camera(c)
            if(d is not None):
                data.append(d)
        # set active camera
        if(len(cams) > 1):
            # if there is just one camera, this behaves badly.
            # use it just when there are two or more cameras..
            active_cam = s.getActiveCamera()
            active_cam_name = active_cam.getName()
            for o in data:
                if(o['type'] == 'CAMERA'):
                    if(o['name'] == active_cam_name):
                        o['active'] = True
        else:
            for o in data:
                if(o['type'] == 'CAMERA'):
                    o['active'] = True
        return data
    
    def sun(self):
        s = self.mxs
        data = []
        env = s.getEnvironment()
        if(env.getSunProperties()[0] == 1):
            log("converting sun..", 2)
            if(env.getSunPositionType() == 2):
                v, _ = env.getSunDirection()
            else:
                v, _ = env.getSunDirectionUsedForRendering()
            d = {'name': "The Sun",
                 'xyz': (v.x(), v.y(), v.z()),
                 'type': 'SUN', }
            data.append(d)
        return data
