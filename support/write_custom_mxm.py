#!/Library/Frameworks/Python.framework/Versions/3.4/bin/python3
# -*- coding: utf-8 -*-

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

import sys
import traceback
import argparse
import textwrap
import json
import os

# from pymaxwell import *


LOG_FILE_PATH = None


def log(msg, indent=0):
    m = "{0}> {1}".format("    " * indent, msg)
    print(m)
    if(LOG_FILE_PATH is not None):
        with open(LOG_FILE_PATH, mode='a', encoding='utf-8', ) as f:
            f.write("{}{}".format(m, "\n"))


def material_placeholder(s, n=None, ):
    if(n is not None):
        # n = '{}_{}'.format(n, 'MATERIAL_PLACEHOLDER')
        pass
    else:
        n = 'MATERIAL_PLACEHOLDER'
    m = s.createMaterial(n)
    l = m.addLayer()
    b = l.addBSDF()
    r = b.getReflectance()
    a = Cattribute()
    a.activeType = MAP_TYPE_BITMAP
    t = CtextureMap()
    mgr = CextensionManager.instance()
    e = mgr.createDefaultTextureExtension('Checker')
    ch = e.getExtensionData()
    ch.setUInt('Number of elements U', 32)
    ch.setUInt('Number of elements V', 32)
    t.addProceduralTexture(ch)
    a.textureMap = t
    r.setAttribute('color', a)
    return m


def material_default(d, s, ):
    m = s.createMaterial(d['name'])
    l = m.addLayer()
    b = l.addBSDF()
    return m


def material_external(d, s, ):
    p = d['path']
    t = s.readMaterial(p)
    t.setName(d['name'])
    m = s.addMaterial(t)
    if(not d['embed']):
        m.setReference(1, p)
    return m


def material_custom(d, s, ):
    m = s.createMaterial(d['name'])
    d = d['data']
    
    def global_props(d, m):
        # global properties
        if(d['override_map']):
            t = texture(d['override_map'], s, )
            if(t is not None):
                m.setGlobalMap(t)
        
        if(d['bump_map_enabled']):
            a = Cattribute()
            a.activeType = MAP_TYPE_BITMAP
            t = texture(d['bump_map'], s, )
            if(t is not None):
                a.textureMap = t
            if(d['bump_map_use_normal']):
                a.value = d['bump_normal']
            else:
                a.value = d['bump']
            m.setAttribute('bump', a)
            m.setNormalMapState(d['bump_map_use_normal'])
        
        m.setDispersion(d['dispersion'])
        m.setMatteShadow(d['shadow'])
        m.setMatte(d['matte'])
        m.setNestedPriority(d['priority'])
        
        c = Crgb()
        c.assign(*d['id'])
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
            if(bp['bump_map_use_normal']):
                a.value = bp['bump_normal']
            else:
                a.value = bp['bump']
            # a.rgb.assign(*bp['transmittance'])
        else:
            a = Cattribute()
            a.activeType = MAP_TYPE_VALUE
            if(bp['bump_map_use_normal']):
                a.value = bp['bump_normal']
            else:
                a.value = bp['bump']
        b.setAttribute('bump', a)
        b.setNormalMapState(bp['bump_map_use_normal'])
        
        if(bp['anisotropy_map_enabled']):
            # # a = texture(bp['anisotropy_map'], s, )
            # t = texture(bp['anisotropy_map'], s, )
            # a = Cattribute()
            # a.textureMap = t
            a = Cattribute()
            a.activeType = MAP_TYPE_BITMAP
            t = texture(bp['anisotropy_map'], s, )
            if(t is not None):
                a.textureMap = t
            a.value = bp['anisotropy']
            # a.rgb.assign(*bp['transmittance'])
        else:
            a = Cattribute()
            a.activeType = MAP_TYPE_VALUE
            a.value = bp['anisotropy']
        b.setAttribute('anisotropy', a)
        
        if(bp['anisotropy_angle_map_enabled']):
            # # a = texture(bp['anisotropy_angle_map'], s, )
            # t = texture(bp['anisotropy_angle_map'], s, )
            # a = Cattribute()
            # a.textureMap = t
            a = Cattribute()
            a.activeType = MAP_TYPE_BITMAP
            t = texture(bp['anisotropy_angle_map'], s, )
            if(t is not None):
                a.textureMap = t
            a.value = bp['anisotropy_angle']
            # a.rgb.assign(*bp['transmittance'])
        else:
            a = Cattribute()
            a.activeType = MAP_TYPE_VALUE
            a.value = bp['anisotropy_angle']
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
            c = Crgb()
            c.assign(*d['color'])
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


def material(d, s, ):
    """create material by type"""
    if(d['subtype'] == 'EXTERNAL'):
        if(d['path'] == ''):
            # m = material_default(d, s)
            m = material_placeholder(s, d['name'])
        else:
            m = material_external(d, s)
            
            if(d['override']):
                # global properties
                if(d['override_map']):
                    t = texture(d['override_map'], s, )
                    if(t is not None):
                        m.setGlobalMap(t)
                
                if(d['bump_map_enabled']):
                    a = Cattribute()
                    a.activeType = MAP_TYPE_BITMAP
                    t = texture(d['bump_map'], s, )
                    if(t is not None):
                        a.textureMap = t
                    if(d['bump_map_use_normal']):
                        a.value = d['bump_normal']
                    else:
                        a.value = d['bump']
                    m.setAttribute('bump', a)
                    m.setNormalMapState(d['bump_map_use_normal'])
                
                m.setDispersion(d['dispersion'])
                m.setMatteShadow(d['shadow'])
                m.setMatte(d['matte'])
                m.setNestedPriority(d['priority'])
                
                c = Crgb()
                c.assign(*d['id'])
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
                    t = texture(d['emitter_spot_map'], s)
                    if(t is not None):
                        e.setLobeImageProjectedMap(d['emitter_spot_map_enabled'], t)
                e.setSpotConeAngle(d['emitter_spot_cone_angle'])
                e.setSpotFallOffAngle(d['emitter_spot_falloff_angle'])
                e.setSpotFallOffType(d['emitter_spot_falloff_type'])
                e.setSpotBlur(d['emitter_spot_blur'])
            
            if(d['emitter_emission'] == 0):
                e.setActiveEmissionType(EMISSION_TYPE_PAIR)
                
                ep = CemitterPair()
                c = Crgb()
                c.assign(*d['emitter_color'])
                ep.rgb.assign(c)
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
                t = texture(d['emitter_hdr_map'], s)
                if(t is not None):
                    a.textureMap = t
                a.value = d['emitter_hdr_intensity']
                e.setMXI(a)
            
            e.setState(True)
            
            def global_props(d, m):
                # global properties
                if(d['override_map']):
                    t = texture(d['override_map'], s, )
                    if(t is not None):
                        m.setGlobalMap(t)
                
                if(d['bump_map_enabled']):
                    a = Cattribute()
                    a.activeType = MAP_TYPE_BITMAP
                    t = texture(d['bump_map'], s, )
                    if(t is not None):
                        a.textureMap = t
                    if(d['bump_map_use_normal']):
                        a.value = d['bump_normal']
                    else:
                        a.value = d['bump']
                    m.setAttribute('bump', a)
                    m.setNormalMapState(d['bump_map_use_normal'])
                
                m.setDispersion(d['dispersion'])
                m.setMatteShadow(d['shadow'])
                m.setMatte(d['matte'])
                m.setNestedPriority(d['priority'])
                
                c = Crgb()
                c.assign(*d['id'])
                m.setColorID(c)
            
            global_props(d, m)
            
        else:
            m = CextensionManager.instance()
            if(d['use'] == 'AGS'):
                e = m.createDefaultMaterialModifierExtension('AGS')
                p = e.getExtensionData()
            
                c = Crgb()
                c.assign(*d['ags_color'])
                p.setRgb('Color', c)
                p.setFloat('Reflection', d['ags_reflection'])
                p.setUInt('Type', d['ags_type'])
            
            elif(d['use'] == 'OPAQUE'):
                e = m.createDefaultMaterialModifierExtension('Opaque')
                p = e.getExtensionData()
            
                p.setByte('Color Type', d['opaque_color_type'])
                c = Crgb()
                c.assign(*d['opaque_color'])
                p.setRgb('Color', c)
                texture_data_to_mxparams(d['opaque_color_map'], p, 'Color Map', )
            
                p.setByte('Shininess Type', d['opaque_shininess_type'])
                p.setFloat('Shininess', d['opaque_shininess'])
                texture_data_to_mxparams(d['opaque_shininess_map'], p, 'Shininess Map', )
            
                p.setByte('Roughness Type', d['opaque_roughness_type'])
                p.setFloat('Roughness', d['opaque_roughness'])
                texture_data_to_mxparams(d['opaque_roughness_map'], p, 'Roughness Map', )
            
                p.setByte('Clearcoat', d['opaque_clearcoat'])
            
            elif(d['use'] == 'TRANSPARENT'):
                e = m.createDefaultMaterialModifierExtension('Transparent')
                p = e.getExtensionData()
            
                p.setByte('Color Type', d['transparent_color_type'])
                c = Crgb()
                c.assign(*d['transparent_color'])
                p.setRgb('Color', c)
                texture_data_to_mxparams(d['transparent_color_map'], p, 'Color Map', )
            
                p.setFloat('Ior', d['transparent_ior'])
                p.setFloat('Transparency', d['transparent_transparency'])
            
                p.setByte('Roughness Type', d['transparent_roughness_type'])
                p.setFloat('Roughness', d['transparent_roughness'])
                texture_data_to_mxparams(d['transparent_roughness_map'], p, 'Roughness Map', )
            
                p.setFloat('Specular Tint', d['transparent_specular_tint'])
                p.setFloat('Dispersion', d['transparent_dispersion'])
                p.setByte('Clearcoat', d['transparent_clearcoat'])
            
            elif(d['use'] == 'METAL'):
                e = m.createDefaultMaterialModifierExtension('Metal')
                p = e.getExtensionData()
            
                p.setUInt('IOR', d['metal_ior'])
            
                p.setFloat('Tint', d['metal_tint'])
            
                p.setByte('Color Type', d['metal_color_type'])
                c = Crgb()
                c.assign(*d['metal_color'])
                p.setRgb('Color', c)
                texture_data_to_mxparams(d['metal_color_map'], p, 'Color Map', )
            
                p.setByte('Roughness Type', d['metal_roughness_type'])
                p.setFloat('Roughness', d['metal_roughness'])
                texture_data_to_mxparams(d['metal_roughness_map'], p, 'Roughness Map', )
            
                p.setByte('Anisotropy Type', d['metal_anisotropy_type'])
                p.setFloat('Anisotropy', d['metal_anisotropy'])
                texture_data_to_mxparams(d['metal_anisotropy_map'], p, 'Anisotropy Map', )
            
                p.setByte('Angle Type', d['metal_angle_type'])
                p.setFloat('Angle', d['metal_angle'])
                texture_data_to_mxparams(d['metal_angle_map'], p, 'Angle Map', )
            
                p.setByte('Dust Type', d['metal_dust_type'])
                p.setFloat('Dust', d['metal_dust'])
                texture_data_to_mxparams(d['metal_dust_map'], p, 'Dust Map', )
            
                p.setByte('Perforation Enabled', d['metal_perforation_enabled'])
                texture_data_to_mxparams(d['metal_perforation_map'], p, 'Perforation Map', )
            
            elif(d['use'] == 'TRANSLUCENT'):
                e = m.createDefaultMaterialModifierExtension('Translucent')
                p = e.getExtensionData()
            
                p.setFloat('Scale', d['translucent_scale'])
                p.setFloat('Ior', d['translucent_ior'])
            
                p.setByte('Color Type', d['translucent_color_type'])
                c = Crgb()
                c.assign(*d['translucent_color'])
                p.setRgb('Color', c)
                texture_data_to_mxparams(d['translucent_color_map'], p, 'Color Map', )
            
                p.setFloat('Hue Shift', d['translucent_hue_shift'])
                p.setByte('Invert Hue', d['translucent_invert_hue'])
                p.setFloat('Vibrance', d['translucent_vibrance'])
                p.setFloat('Density', d['translucent_density'])
                p.setFloat('Opacity', d['translucent_opacity'])
            
                p.setByte('Roughness Type', d['translucent_roughness_type'])
                p.setFloat('Roughness', d['translucent_roughness'])
                texture_data_to_mxparams(d['translucent_roughness_map'], p, 'Roughness Map', )
            
                p.setFloat('Specular Tint', d['translucent_specular_tint'])
                p.setByte('Clearcoat', d['translucent_clearcoat'])
                p.setFloat('Clearcoat Ior', d['translucent_clearcoat_ior'])
            
            elif(d['use'] == 'CARPAINT'):
                e = m.createDefaultMaterialModifierExtension('Car Paint')
                p = e.getExtensionData()
            
                c = Crgb()
                c.assign(*d['carpaint_color'])
                p.setRgb('Color', c)
            
                p.setFloat('Metallic', d['carpaint_metallic'])
                p.setFloat('Topcoat', d['carpaint_topcoat'])
            
            elif(d['use'] == 'HAIR'):
                e = m.createDefaultMaterialModifierExtension('Hair')
                p = e.getExtensionData()
                
                p.setByte('Color Type', d['hair_color_type'])
                
                c = Crgb()
                c.assign(*d['hair_color'])
                p.setRgb('Color', c)
                texture_data_to_mxparams(d['hair_color_map'], p, 'Color Map', )
                
                texture_data_to_mxparams(d['hair_root_tip_map'], p, 'Root-Tip Map', )
                
                p.setByte('Root-Tip Weight Type', d['hair_root_tip_weight_type'])
                p.setFloat('Root-Tip Weight', d['hair_root_tip_weight'])
                texture_data_to_mxparams(d['hair_root_tip_weight_map'], p, 'Root-Tip Weight Map', )
                
                p.setFloat('Primary Highlight Strength', d['hair_primary_highlight_strength'])
                p.setFloat('Primary Highlight Spread', d['hair_primary_highlight_spread'])
                c = Crgb()
                c.assign(*d['hair_primary_highlight_tint'])
                p.setRgb('Primary Highlight Tint', c)
                
                p.setFloat('Secondary Highlight Strength', d['hair_secondary_highlight_strength'])
                p.setFloat('Secondary Highlight Spread', d['hair_secondary_highlight_spread'])
                c = Crgb()
                c.assign(*d['hair_secondary_highlight_tint'])
                p.setRgb('Secondary Highlight Tint', c)
            
            m = s.createMaterial(d['name'])
            m.applyMaterialModifierExtension(p)
            
            # global properties
            if(d['override_map']):
                t = texture(d['override_map'], s, )
                if(t is not None):
                    m.setGlobalMap(t)
            
            if(d['bump_map_enabled']):
                a = Cattribute()
                a.activeType = MAP_TYPE_BITMAP
                t = texture(d['bump_map'], s, )
                if(t is not None):
                    a.textureMap = t
                if(d['bump_map_use_normal']):
                    a.value = d['bump_normal']
                else:
                    a.value = d['bump']
                m.setAttribute('bump', a)
                m.setNormalMapState(d['bump_map_use_normal'])
            
            m.setDispersion(d['dispersion'])
            m.setMatteShadow(d['shadow'])
            m.setMatte(d['matte'])
            
            m.setNestedPriority(d['priority'])
            
            c = Crgb()
            c.assign(*d['id'])
            m.setColorID(c)
            
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
            
            try:
                displacement(d['displacement'], m)
            except KeyError:
                pass
            
    elif(d['subtype'] == 'CUSTOM'):
        m = material_custom(d, s, )
    else:
        raise TypeError("Material '{}' {} is unknown type".format(d['name'], d['subtype']))
    return m


def texture(d, s, ):
    if(d is None):
        return
    
    t = CtextureMap()
    t.setPath(d['path'])
    
    t.uvwChannelID = d['channel']
    
    t.brightness = d['brightness'] / 100
    t.contrast = d['contrast'] / 100
    t.saturation = d['saturation'] / 100
    t.hue = d['hue'] / 180
    
    t.useGlobalMap = d['use_global_map']
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
    
    t.normalMappingFlipRed = d['normal_mapping_flip_red']
    t.normalMappingFlipGreen = d['normal_mapping_flip_green']
    t.normalMappingFullRangeBlue = d['normal_mapping_full_range_blue']
    
    # t.cosA
    # t.doGammaCorrection
    # t.sinA
    # t.theTextureExtensions
    
    return t


def texture_data_to_mxparams(d, mp, name, ):
    if(d is None):
        return
    
    # t = mp.getTextureMap(name)[0]
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
    
    t.normalMappingFlipRed = d['normal_mapping_flip_red']
    t.normalMappingFlipGreen = d['normal_mapping_flip_green']
    t.normalMappingFullRangeBlue = d['normal_mapping_full_range_blue']
    
    t.useAlpha = d['alpha_only']
    t.typeInterpolation = d['interpolation']
    
    t.brightness = d['brightness'] / 100
    t.contrast = d['contrast'] / 100
    t.hue = d['hue'] / 180
    t.saturation = d['saturation'] / 100
    
    t.clampMin = d['rgb_clamp'][0] / 255
    t.clampMax = d['rgb_clamp'][1] / 255
    
    t.useGlobalMap = d['use_global_map']
    # t.cosA = 1.000000
    # t.sinA = 0.000000
    ok = mp.setTextureMap(name, t)
    
    return mp


def main(args):
    log("loading data..", 2)
    with open(args.data_path, 'r') as f:
        data = json.load(f)
    
    log("creating material..", 2)
    mxs = Cmaxwell(mwcallback)
    
    m = CextensionManager.instance()
    m.loadAllExtensions()
    
    m = material(data, mxs, )
    
    if(m is not None):
        m.write(args.result_path)
    else:
        raise RuntimeError("Something unexpected happened..")
    
    log("done.", 2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=textwrap.dedent('''Make Maxwell Custom Material from serialized data'''), epilog='',
                                     formatter_class=argparse.RawDescriptionHelpFormatter, add_help=True, )
    parser.add_argument('pymaxwell_path', type=str, help='path to directory containing pymaxwell')
    parser.add_argument('log_file', type=str, help='path to log file')
    parser.add_argument('data_path', type=str, help='path to serialized material data file')
    parser.add_argument('result_path', type=str, help='path to result .mxs')
    args = parser.parse_args()
    
    PYMAXWELL_PATH = args.pymaxwell_path
    
    try:
        from pymaxwell import *
    except ImportError:
        sys.path.insert(0, PYMAXWELL_PATH)
        from pymaxwell import *
    
    LOG_FILE_PATH = args.log_file
    
    try:
        main(args)
    except Exception as e:
        import traceback
        m = traceback.format_exc()
        log(m)
        sys.exit(1)
    sys.exit(0)
