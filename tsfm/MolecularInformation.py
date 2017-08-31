# -*- coding: utf-8 -*-
from collections import Counter, defaultdict
from multiprocessing import Pool
from operator import itemgetter
from string import Template
from ast import literal_eval as make_tuple
import bisect
import pkgutil
import itertools
import sys
import numpy as np
import tsfm.nsb_entropy as nb
import random
import time
import math as mt
import tsfm.exact as exact
import glob
import re
import statsmodels.stats.multitest as smm
import pandas as pd


class DistanceCalculator:
    def __init__(self, distance):
        self.distanceMetric = distance
        self.featureSet = set()
        self.functionSet = set()

    def get_distance(self, ResultsDict):
        for result in ResultsDict:
            for coord in ResultsDict[result].basepairs:
                if (coord in ResultsDict[result].info):
                    for pairtype in ResultsDict[result].info[coord]:
                        self.featureSet.add("{}{}".format("".join(str(i) for i in coord), pairtype))
                        for function in ResultsDict[result].height[coord][pairtype]:
                            self.functionSet.add(function)
            
            for coord in range(ResultsDict[result].pos):
                if (coord in ResultsDict[result].info):
                    for base in ResultsDict[result].info[coord]:
                        self.featureSet.add("{}{}".format(coord, base))
                        for function in ResultsDict[result].height[coord][base]:
                            self.functionSet.add(function)

        #add inverse info features
            for coord in ResultsDict[result].basepairs:
                if (coord in ResultsDict[result].inverseInfo):
                    for pairtype in ResultsDict[result].inverseInfo[coord]:
                        self.featureSet.add("i{}{}".format("".join(str(i) for i in coord), pairtype))
        
            for coord in range(ResultsDict[result].pos):
                if (coord in ResultsDict[result].inverseInfo):
                    for base in ResultsDict[result].inverseInfo[coord]:
                        self.featureSet.add("i{}{}".format(coord, base))

        #remove features that contain gaps
        self.featureSet = {feature for feature in self.featureSet if not "-" in feature}

        #prepare pandas dataframes for each result object
        functionDict = {}
        pandasDict = {}
        for function in self.functionSet:
            functionDict[function] = np.zeros(len(self.featureSet),)
        functionDict["bits"] = np.zeros(len(self.featureSet),)
        
        for result in ResultsDict:
            pandasDict[result] = pd.DataFrame(functionDict, index = self.featureSet)
            for coord in ResultsDict[result].basepairs:
                if (coord in ResultsDict[result].info):
                    for pairtype in [pair for pair in ResultsDict[result].info[coord] if not "-" in pair]:
                        row = "{}{}".format("".join(str(i) for i in coord), pairtype)
                        pandasDict[result].loc[row, "bits"] = ResultsDict[result].info[coord][pairtype] 
                        for function in ResultsDict[result].height[coord][pairtype]:
                            pandasDict[result].loc[row, function] = ResultsDict[result].height[coord][pairtype][function]
            
            for coord in range(ResultsDict[result].pos):
                if (coord in ResultsDict[result].info):
                    for base in [nuc for nuc in ResultsDict[result].info[coord] if not nuc == "-"]:
                        row = "{}{}".format(coord, base)
                        pandasDict[result].loc[row, "bits"] = ResultsDict[result].info[coord][base]
                        for function in ResultsDict[result].height[coord][base]:
                            pandasDict[result].loc[row, function] = ResultsDict[result].height[coord][base][function]

            for coord in ResultsDict[result].basepairs:
                if (coord in ResultsDict[result].inverseInfo):
                    for pairtype in [pair for pair in ResultsDict[result].inverseInfo[coord] if not "-" in pair]:
                        row = "i{}{}".format("".join(str(i) for i in coord), pairtype)
                        pandasDict[result].loc[row, "bits"] = ResultsDict[result].inverseInfo[coord][pairtype] 
                        for function in ResultsDict[result].inverseHeight[coord][pairtype]:
                            pandasDict[result].loc[row, function] = ResultsDict[result].inverseHeight[coord][pairtype][function]
            
            for coord in range(ResultsDict[result].pos):
                if (coord in ResultsDict[result].inverseInfo):
                    for base in [nuc for nuc in ResultsDict[result].inverseInfo[coord] if not nuc == "-"]:
                        row = "i{}{}".format(coord, base)
                        pandasDict[result].loc[row, "bits"] = ResultsDict[result].inverseInfo[coord][base]
                        for function in ResultsDict[result].inverseHeight[coord][base]:
                            pandasDict[result].loc[row, function] = ResultsDict[result].inverseHeight[coord][base][function]
        
        #normalize heights to equal one after possible removal of CIFs based on some criteria 
        for frame in pandasDict:
            pandasDict[frame] = pandasDict[frame].round(3)
            pandasDict[frame].drop('bits', axis=1).div(pandasDict[frame].drop('bits', axis=1).sum(axis=1), axis=0)

        if (self.distanceMetric == "jsd"):
            self.rJSD(pandasDict)


    def rJSD(self, pandasDict):
        pairwise_combinations = itertools.permutations(pandasDict.keys(), 2)
        jsdDistMatrix = pd.DataFrame(index=list(pandasDict.keys()), columns = list(pandasDict.keys()))
        jsdDistMatrix = jsdDistMatrix.fillna(0)
        for pair in pairwise_combinations:
            distance = 0
            for i, row in pandasDict[pair[0]].iterrows():
                if (row['bits'] == 0 and pandasDict[pair[1]].loc[i, 'bits'] == 0):
                    continue
                else:
                    distance += self.rJSD_distance(row.drop('bits').as_matrix(), 
                                                pandasDict[pair[1]].loc[i,].drop('bits').as_matrix(),
                                                row['bits'], pandasDict[pair[1]].loc[i, 'bits'])
            
            jsdDistMatrix.loc[pair[0], pair[1]] = distance
        
        print(jsdDistMatrix)

    def entropy(self, dist):
        return np.sum(-dist[dist!=0]*np.log2(dist[dist!=0]))

    def rJSD_distance(self, dist1, dist2, pi1, pi2):
        step = self.entropy(pi1*dist1+pi2*dist2) - (pi1*self.entropy(dist1) + pi2*self.entropy(dist2))
        return (pi1+pi2)*mt.sqrt(step if step >= 0 else 0)

class FunctionLogoResults:
    def __init__(self, name, basepairs = [], pos = 0, sequences = [], pairs = set(), singles = set(), info = {},
                 height = {}, inverseInfo = {}, inverseHeight = {}, p = {},
                 inverse_p = {}, from_file = False):
        if (not info):
            self.info = defaultdict(lambda : defaultdict(float))
            self.height = defaultdict(lambda : defaultdict(lambda : defaultdict(float)))
        else:
            self.info = info
            self.height = height
        
        if (not inverseInfo):
            self.inverseInfo = defaultdict(lambda : defaultdict(float))
            self.inverseHeight = defaultdict(lambda : defaultdict(lambda : defaultdict(float)))
        else:
            self.inverseInfo = inverseInfo
            self.inverseHeight = inverseHeight

        if (not p):
            self.p = {'P': defaultdict(lambda: defaultdict(float)), 
                      'p': defaultdict(lambda: defaultdict(lambda: defaultdict(float))),
                      'P_corrected': defaultdict(lambda: defaultdict(float)),
                      'p_corrected': defaultdict(lambda: defaultdict(lambda: defaultdict(float)))} 
        else:
            self.p = p

        if (not inverse_p):
            self.inverse_p = {'P': defaultdict(lambda: defaultdict(float)), 
                      'p': defaultdict(lambda: defaultdict(lambda: defaultdict(float))),
                      'P_corrected': defaultdict(lambda: defaultdict(float)),
                      'p_corrected': defaultdict(lambda: defaultdict(lambda: defaultdict(float)))} 
        else:
            self.inverse_p = inverse_p
        
        self.correction = ""
        self.basepairs = basepairs
        self.pos = pos
        self.sequences = sequences
        self.pairs = pairs
        self.singles = singles

        if (from_file):
            self.name = name.split("/")[-1]
            self.from_file(name)
        else:
            self.name = name

    def from_file(self, file_name):
        pvalue = False
        file_handle = open(file_name, "r")
        for line in file_handle:
            if (line.startswith("#")):
                if ("p-value" in line):
                    pvalue = True
            else:
                line = line.strip()
                spline = line.split("\t")
                if (spline[0] == "bp:"):
                    if (not make_tuple(spline[1]) in self.basepairs):
                        self.basepairs.append(make_tuple(spline[1]))
                    self.pairs.add(spline[2])
                    self.info[make_tuple(spline[1])][spline[2]] = float(spline[4])
                    if (pvalue):
                        self.p['P'][make_tuple(spline[1])][spline[2]] = float(spline[5])
                        self.p['P_corrected'][make_tuple(spline[1])][spline[2]] = float(spline[6])
                    for function in spline[7].split():
                        function_split = function.split(":")
                        self.height[make_tuple(spline[1])][spline[2]][function_split[0]] = float(function_split[1])
                        if (pvalue):
                            self.p['p'][make_tuple(spline[1])][spline[2]][function_split[0]] = float(function_split[2])
                            self.p['p_corrected'][make_tuple(spline[1])][spline[2]][function_split[0]] = float(function_split[3])
                elif (spline[0] == "ss:"):
                    if (self.pos < int(spline[1])):
                        self.pos = int(spline[1])
                    self.singles.add(spline[2])
                    self.info[int(spline[1])][spline[2]] = float(spline[4])
                    if (pvalue):
                        self.p['P'][int(spline[1])][spline[2]] = float(spline[5])
                        self.p['P_corrected'][int(spline[1])][spline[2]] = float(spline[6])
                    for function in spline[7].split():
                        function_split = function.split(":")
                        self.height[int(spline[1])][spline[2]][function_split[0]] = float(function_split[1])
                        if (pvalue):
                            self.p['p'][int(spline[1])][spline[2]][function_split[0]] = float(function_split[2])
                            self.p['p_corrected'][int(spline[1])][spline[2]][function_split[0]] = float(function_split[3])
                elif (spline[0] == "ibp:"):
                    if (not make_tuple(spline[1]) in self.basepairs):
                        self.basepairs.append(make_tuple(spline[1]))
                    self.pairs.add(spline[2])
                    self.inverseInfo[make_tuple(spline[1])][spline[2]] = float(spline[4])
                    if (pvalue):
                        self.inverse_p['P'][make_tuple(spline[1])][spline[2]] = float(spline[5])
                        self.inverse_p['P_corrected'][make_tuple(spline[1])][spline[2]] = float(spline[6])
                    for function in spline[7].split():
                        function_split = function.split(":")
                        self.inverseHeight[make_tuple(spline[1])][spline[2]][function_split[0]] = float(function_split[1])
                        if (pvalue):
                            self.inverse_p['p'][make_tuple(spline[1])][spline[2]][function_split[0]] = float(function_split[2])
                            self.inverse_p['p_corrected'][make_tuple(spline[1])][spline[2]][function_split[0]] = float(function_split[3])
                elif (spline[0] == "iss:"):
                    if (self.pos < int(spline[1])):
                        self.pos = int(spline[1])
                    self.singles.add(spline[2])
                    self.inverseInfo[int(spline[1])][spline[2]] = float(spline[4])
                    if (pvalue):
                        self.inverse_p['P'][int(spline[1])][spline[2]] = float(spline[5])
                        self.inverse_p['P_corrected'][int(spline[1])][spline[2]] = float(spline[6])
                    for function in spline[7].split():
                        function_split = function.split(":")
                        self.inverseHeight[int(spline[1])][spline[2]][function_split[0]] = float(function_split[1])
                        if (pvalue):
                            self.inverse_p['p'][int(spline[1])][spline[2]][function_split[0]] = float(function_split[2])
                            self.inverse_p['p_corrected'][int(spline[1])][spline[2]][function_split[0]] = float(function_split[3])
        self.pos += 1 #fix off by one
        file_handle.close()

    def add_information(self, info, height, inverse = False):
        if (inverse):
            self.inverseInfo = info
            self.inverseHeight = height
        else:
            self.info = info
            self.height = height
    
    def add_stats(self, distribution, correction, inverse = False):
        self.correction = correction
        if (inverse):
            self.inverse_p = distribution.stat_test(self.inverseInfo, self.inverseHeight,
                                                    correction)
        else:
            self.p = distribution.stat_test(self.info, self.height, correction)

    def get(self, position, state):
        ret_counter = Counter()
        if (len(position) == 1):
            for x in self.sequences:
                if (x.seq[position[0]] == state[0]):
                    ret_counter[x.function] += 1
        if (len(position) == 2):
            for x in self.sequences:
                if (x.seq[position[0]] == state[0] and x.seq[position[1]] == state[1]):
                    ret_counter[x.function] += 1

        return ret_counter

    def text_output(self):
        #build output heading
        file_handle = open("{}_results.txt".format(self.name.split("/")[-1]), "w")
        heading_dict = {}
        if (self.p):
            heading_dict['P'] = "\tp-value\t{}".format(self.correction)
            heading_dict['p'] =  "\tclass:height:p-value:{}".format(self.correction)
        else:
            heading_dict['P'] = ""
            heading_dict['p'] = "\tclass:height"

        print("#bp\tcoord\tstate\tN\tinfo{P}{p}".format(**heading_dict), file = file_handle)
        for coord in sorted(self.basepairs, key = itemgetter(0)):
            if (coord in self.info):
                for pairtype in sorted(self.info[coord]):
                    output_string = "bp:\t{}".format(coord)
                    output_string += "\t{}\t{}\t{:05.3f}\t".format(pairtype, sum(self.get(coord, pairtype).values()), self.info[coord][pairtype])
                    if (self.p):
                        output_string += "{:08.6f}".format(self.p['P'][coord][pairtype])
                        output_string += "\t{:08.6f}".format(self.p['P_corrected'][coord][pairtype])

                    output_string += "\t"
                    for aainfo in sorted(self.height[coord][pairtype].items(), key = itemgetter(1), reverse = True):
                        output_string += "{}:{:05.3f}".format(aainfo[0], aainfo[1])
                        if (self.p):
                            output_string += ":{:08.6f}".format(self.p['p'][coord][pairtype][aainfo[0].upper()])
                            output_string += ":{:08.6f}".format(self.p['p_corrected'][coord][pairtype][aainfo[0].upper()])
                        output_string += " "

                    print(output_string, file = file_handle)

        if (self.inverseInfo):
            print("#ibp\tcoord\tstate\tN\tinfo{P}{p}".format(**heading_dict), file = file_handle)
        for coord in sorted(self.basepairs, key = itemgetter(0)):
            if (coord in self.inverseInfo):
                for pairtype in sorted(self.inverseInfo[coord]):
                    output_string = "ibp:\t{}".format(coord)
                    output_string += "\t{}\t{}\t{:05.3f}\t".format(pairtype, sum(self.get(coord, pairtype).values()), self.inverseInfo[coord][pairtype])
                    if (self.p):
                        output_string += "{:08.6f}".format(self.inverse_p['P'][coord][pairtype])
                        output_string += "\t{:08.6f}".format(self.inverse_p['P_corrected'][coord][pairtype])

                    output_string += "\t"
                    for aainfo in sorted(self.inverseHeight[coord][pairtype].items(), key = itemgetter(1), reverse = True):
                        output_string += "{}:{:05.3f}".format(aainfo[0], aainfo[1])
                        if (self.p):
                            output_string += ":{:08.6f}".format(self.inverse_p['p'][coord][pairtype][aainfo[0].upper()])
                            output_string += ":{:08.6f}".format(self.inverse_p['p_corrected'][coord][pairtype][aainfo[0].upper()])
                        output_string += " "

                    print(output_string, file = file_handle)

        print("#ss\tcoord\tstate\tN\tinfo{P}{p}".format(**heading_dict), file = file_handle)
        for coord in range(self.pos):
            if (coord in self.info):
                for base in sorted(self.info[coord]):
                    output_string = "ss:\t{}\t{}\t{}\t{:05.3f}".format(coord, base,
                                                                         sum(self.get([coord], base).values()),
                                                                         self.info[coord][base])
                    if (self.p):
                        output_string += "\t{:08.6f}".format(self.p['P'][coord][base])
                        output_string += "\t{:08.6f}".format(self.p['P_corrected'][coord][base])

                    output_string += "\t"
                    for aainfo in sorted(self.height[coord][base].items(), key = itemgetter(1), reverse = True):
                        output_string += "{}:{:05.3f}".format(aainfo[0], aainfo[1])
                        if (self.p):
                            output_string += ":{:08.6f}".format(self.p['p'][coord][base][aainfo[0].upper()])
                            output_string += ":{:08.6f}".format(self.p['p_corrected'][coord][base][aainfo[0].upper()])
                        output_string += " "

                    print(output_string, file = file_handle)

        if (self.inverseInfo):
            print("#iss\tcoord\tstate\tN\tinfo{P}{p}".format(**heading_dict), file = file_handle)
        for coord in range(self.pos):
            if (coord in self.inverseInfo):
                for base in sorted(self.inverseInfo[coord]):
                    output_string = "iss:\t{}\t{}\t{}\t{:05.3f}".format(coord, base,
                                                                         sum(self.get([coord], base).values()),
                                                                         self.inverseInfo[coord][base])
                    if (self.p):
                        output_string += "\t{:08.6f}".format(self.inverse_p['P'][coord][base])
                        output_string += "\t{:08.6f}".format(self.inverse_p['P_corrected'][coord][base])

                    output_string += "\t"
                    for aainfo in sorted(self.inverseHeight[coord][base].items(), key = itemgetter(1), reverse = True):
                        output_string += "{}:{:05.3f}".format(aainfo[0], aainfo[1])
                        if (self.p):
                            output_string += ":{:08.6f}".format(self.inverse_p['p'][coord][base][aainfo[0].upper()])
                            output_string += ":{:08.6f}".format(self.inverse_p['p_corrected'][coord][base][aainfo[0].upper()])
                        output_string += " "

                    print(output_string, file = file_handle)
        file_handle.close()

    def logo_output(self):
        coord_length = 0 #used to determine eps height
        coord_length_addition = 0

        logo_outputDict = defaultdict(lambda : defaultdict(lambda : defaultdict(float)))
        inverse_logo_outputDict = defaultdict(lambda : defaultdict(lambda : defaultdict(float)))

        #logo output dict construction
        for coord in sorted(self.basepairs, key = itemgetter(0)):
            for pairtype in sorted(self.pairs):
                if (pairtype in self.info[coord]):
                    for aainfo in sorted(self.height[coord][pairtype].items(), key = itemgetter(1), reverse = True):
                        logo_outputDict[pairtype][coord][aainfo[0]] = self.info[coord][pairtype] * aainfo[1]
                else:
                    logo_outputDict[pairtype][coord] = {}

        for coord in range(self.pos):
            for base in sorted(self.singles):
                if (base in self.info[coord]):
                    for aainfo in sorted(self.height[coord][base].items(), key = itemgetter(1), reverse = True):
                        logo_outputDict[base][coord][aainfo[0]] = self.info[coord][base] * aainfo[1]
                else:
                    logo_outputDict[base][coord] = {}

        #inverse logo output dict construction
        for coord in sorted(self.basepairs, key = itemgetter(0)):
            for pairtype in sorted(self.pairs):
                if (pairtype in self.inverseInfo[coord]):
                    for aainfo in sorted(self.inverseHeight[coord][pairtype].items(), key = itemgetter(1), reverse = True):
                        inverse_logo_outputDict[pairtype][coord][aainfo[0]] = self.inverseInfo[coord][pairtype] * aainfo[1]
                else:
                    inverse_logo_outputDict[pairtype][coord] = {}

        for coord in range(self.pos):
            for base in sorted(self.singles):
                if (base in self.inverseInfo[coord]):
                    for aainfo in sorted(self.inverseHeight[coord][base].items(), key = itemgetter(1), reverse = True):
                        inverse_logo_outputDict[base][coord][aainfo[0]] = self.inverseInfo[coord][base] * aainfo[1]
                else:
                    inverse_logo_outputDict[base][coord] = {}

        #output logos
        for base in logo_outputDict:
            logodata = ""
            for coord in sorted(logo_outputDict[base].keys()):
                if (len(str(coord)) > coord_length):
                    coord_length = len(str(coord))
                logodata += "numbering {{({}) makenumber}} if\ngsave\n".format(coord)
                for aainfo in sorted(logo_outputDict[base][coord].items(), key = itemgetter(1)):
                    if (aainfo[1] < 0.0001 or mt.isnan(aainfo[1])):
                        continue
                    logodata += "{:07.5f} ({}) numchar\n".format(aainfo[1], aainfo[0].upper())
                logodata += "grestore\nshift\n"
            #output logodata to template
            template_byte = pkgutil.get_data('bplogofuntest', 'eps/Template.eps')
            logo_template = template_byte.decode('utf-8')
            with open("{}_{}.eps".format(base, self.name.split("/")[-1]), "w") as logo_output:
                src = Template(logo_template)
                if (len(base) == 2):
                    logodata_dict = {'logo_data': logodata, 'low': min(logo_outputDict[base].keys()), 'high': max(logo_outputDict[base].keys()), 'length': 21 * len(logo_outputDict[base].keys()), 'height': 735-(5*(coord_length + coord_length_addition))}
                else:
                    logodata_dict = {'logo_data': logodata, 'low': min(logo_outputDict[base].keys()), 'high': max(logo_outputDict[base].keys()), 'length': 15.68 * len(logo_outputDict[base].keys()), 'height': 735-(5*(coord_length + coord_length_addition))}
                logo_output.write(src.substitute(logodata_dict))

        for base in inverse_logo_outputDict:
            logodata = ""
            for coord in sorted(inverse_logo_outputDict[base].keys()):
                if (len(str(coord)) > coord_length):
                    coord_length = len(str(coord))
                logodata += "numbering {{({}) makenumber}} if\ngsave\n".format(coord)
                for aainfo in sorted(inverse_logo_outputDict[base][coord].items(), key = itemgetter(1)):
                    if (aainfo[1] < 0.0001 or mt.isnan(aainfo[1])):
                        continue
                    logodata += "{:07.5f} ({}) numchar\n".format(aainfo[1], aainfo[0].upper())
                logodata += "grestore\nshift\n"
            #output logodata to template
            template_byte = pkgutil.get_data('bplogofuntest', 'eps/Template.eps')
            logo_template = template_byte.decode('utf-8')
            with open("inverse_{}_{}.eps".format(base, self.name.split("/")[-1]), "w") as logo_output:
                src = Template(logo_template)
                if (len(base) == 2):
                    logodata_dict = {'logo_data': logodata, 'low': min(inverse_logo_outputDict[base].keys()), 'high': max(inverse_logo_outputDict[base].keys()), 'length': 21 * len(inverse_logo_outputDict[base].keys()), 'height': 735-(5*(coord_length + coord_length_addition))}
                else:
                    logodata_dict = {'logo_data': logodata, 'low': min(inverse_logo_outputDict[base].keys()), 'high': max(inverse_logo_outputDict[base].keys()), 'length': 15.68 * len(inverse_logo_outputDict[base].keys()), 'height': 735-(5*(coord_length + coord_length_addition))}
                logo_output.write(src.substitute(logodata_dict))

class FunctionLogoDist:
    def __init__(self):

        self.bpinfodist = defaultdict(int)
        self.bpheightdist = defaultdict(int)

        self.singleinfodist = defaultdict(int)
        self.singleheightdist = defaultdict(int)

    def weighted_dist(self, bpdata, singledata):
        for x in bpdata[0]:
            self.bpinfodist[x] += 1
        for x in bpdata[1]:
            self.bpheightdist[x] += 1

        for x in singledata[0]:
            self.singleinfodist[x] += 1
        for x in singledata[1]:
            self.singleheightdist[x] += 1

        self.bpinfo_sorted_keys = sorted(self.bpinfodist.keys())
        self.bpheight_sorted_keys = sorted(self.bpheightdist.keys())
        self.ssinfo_sorted_keys = sorted(self.singleinfodist.keys())
        self.ssheight_sorted_keys = sorted(self.singleheightdist.keys())

    def stat_test(self, info, height, correction):
        P = defaultdict(lambda: defaultdict(float))
        P_corrected = defaultdict(lambda: defaultdict(float))
        p = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
        p_corrected = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
        bp_coords = []
        ss_coords = []
        for coord in info:
            for pairtype in info[coord]:
                if ("," in str(coord)):
                    bp_coords.append(coord)
                    P[coord][pairtype] = self.rtp(self.bpinfodist, info[coord][pairtype], self.bpinfo_sorted_keys)
                    for aa in height[coord][pairtype]:
                        p[coord][pairtype][aa] = self.rtp(self.bpheightdist, info[coord][pairtype]*height[coord][pairtype][aa],
                                                          self.bpheight_sorted_keys)
                else:
                    ss_coords.append(coord)
                    P[coord][pairtype] = self.rtp(self.singleinfodist, info[coord][pairtype], self.ssinfo_sorted_keys)
                    for aa in height[coord][pairtype]:
                        p[coord][pairtype][aa] = self.rtp(self.singleheightdist, info[coord][pairtype]*height[coord][pairtype][aa],
                                                          self.ssheight_sorted_keys)
        test_bp = []
        test_ss = []
        bp_coords.sort()
        ss_coords.sort()
        for coord in bp_coords:
            for pairtype in sorted(P[coord]):
                    test_bp.append(P[coord][pairtype])

        for coord in ss_coords:
            for pairtype in sorted(P[coord]):
                test_ss.append(P[coord][pairtype])

        test_bp_results = smm.multipletests(test_bp, method = correction)[1].tolist()
        test_ss_results = smm.multipletests(test_ss, method = correction)[1].tolist()

        for coord in bp_coords:
            for pairtype in sorted(P[coord]):
                P_corrected[coord][pairtype] = test_bp_results.pop(0)

        for coord in ss_coords:
            for pairtype in sorted(P[coord]):
                P_corrected[coord][pairtype] = test_ss_results.pop(0)

        test_bp = []
        test_ss = []
        for coord in bp_coords:
            for pairtype in sorted(p[coord]):
                for aa in sorted(p[coord][pairtype]):
                    test_bp.append(p[coord][pairtype][aa])

        for coord in ss_coords:
            for pairtype in sorted(p[coord]):
                for aa in sorted(p[coord][pairtype]):
                    test_ss.append(p[coord][pairtype][aa])

        test_bp_results = smm.multipletests(test_bp, method = correction)[1].tolist()
        test_ss_results = smm.multipletests(test_ss, method = correction)[1].tolist()

        for coord in bp_coords:
            for pairtype in sorted(p[coord]):
                for aa in sorted(p[coord][pairtype]):
                    p_corrected[coord][pairtype][aa] = test_bp_results.pop(0)

        for coord in ss_coords:
            for pairtype in sorted(p[coord]):
                for aa in sorted(p[coord][pairtype]):
                    p_corrected[coord][pairtype][aa] = test_ss_results.pop(0)
        
        return {'P': P, 'p': p, "P_corrected": P_corrected, "p_corrected": p_corrected} 

    def rtp(self, data, point, keys_sorted):
        if (point > 0):
            part = 0
            total = sum(data.values())
            i = bisect.bisect_left(keys_sorted, point)
            if (point <= keys_sorted[-1]):
                for y in keys_sorted[i:]:
                    part += data[y]
                return part / total
            else:
                return 0.0
        else:
            return 1.0

class Seq:
    def __init__(self, function, seq):
        self.function = function
        self.seq = seq

    def __len__(self):
        return len(self.seq)


class FunctionLogo:
    def __init__(self, struct_file, kind = None, exact = [], inverse = []):
        if (kind):
            self.parse_struct(struct_file, kind)
            self.exact = []
            self.inverse_exact = []
        else:
            self.basepairs = struct_file
            self.exact = exact
            self.inverse_exact = inverse
        self.pos = 0
        self.sequences = []
        self.pairs = set()
        self.singles = set()
        self.functions = Counter()

    def parse_sequences(self, file_prefix):
        for fn in glob.glob("{}_?.aln".format(file_prefix)):
            match = re.search("_([A-Z])\.aln", fn)
            aa_class = match.group(1)
            with open(fn, "r") as ALN:
                good = False
                begin_seq = False
                interleaved = False
                seq = {}
                for line in ALN:
                    match = re.search("^(\S+)\s+(\S+)", line)
                    if (re.search("^CLUSTAL", line)):
                        good = True
                        continue
                    elif (re.search("^[\s\*\.\:]+$", line) and not interleaved and begin_seq):
                        interleaved = True
                    elif (re.search("^[\s\*\.\:]+$", line) and interleaved and begin_seq):
                        continue
                    elif (match and not interleaved):
                        begin_seq = True
                        if (not good):
                            sys.exit("File {} appears not to be a clustal file".format(fn))
                        seq[match.group(1)] = match.group(2)
                    elif (match and interleaved):
                        seq[match.group(1)] += match.group(2)
            for sequence in seq.values():
                self.add_sequence(aa_class, sequence.upper().replace("T", "U"))

        print("{} alignments parsed".format(len(self.functions.keys())), file=sys.stderr)

    def parse_struct(self, struct_file, kind):
        print("Parsing base-pair coordinates", file=sys.stderr)
        basepairs = []
        if (kind == "cove"):
            ss = ""
            pairs = defaultdict(list)
            tarm = 0
            stack = []
            for line in struct_file:
                line = line.strip()
                ss += line.split()[1]
            struct_file.seek(0)

            state = "start"
            for count, i in enumerate(ss):
                if (i == ">" and (state == "start" or state == "AD")):
                    if (state == "start"):
                        state = "AD"
                    stack.append(count)

                elif (i == "<" and (state == "AD" or state == "D")):
                    if (state == "AD"):
                        state = "D"
                    pairs[state].append([stack.pop(), count])

                elif (i == ">" and (state == "D" or state == "C")):
                    if (state == "D"):
                        state = "C"
                    stack.append(count)

                elif (i == "<" and (state == "C" or state == "cC")):
                    if (state == "C"):
                        state = "cC"
                    pairs["C"].append([stack.pop(), count])

                elif (i == ">" and (state == "cC" or state == "T")):
                    if (state == "cC"):
                        state = "T"
                    stack.append(count)
                    tarm += 1

                elif (i == "<" and (state == "T" and tarm > 0)):
                    pairs[state].append([stack.pop(), count])
                    tarm -= 1

                elif (i == "<" and (state == "T" or state == "A") and tarm == 0):
                    state = "A"
                    pairs[state].append([stack.pop(), count])

            for arm in pairs:
                for pair in pairs[arm]:
                    basepairs.append((pair[0], pair[1]))


        if (kind == "text"):
            for line in struct_file:
                line = line.split(";")[1]
                coords = line.split(",")
                for coord in coords:
                    pos = coord.split(":")
                    pos = [int(x) for x in pos]
                    basepairs.append((pos[0], pos[1]))

        self.basepairs = basepairs

    def approx_expect(self, H, k, N):
        return H - ((k - 1)/((mt.log(4)) * N))

    def exact_run(self, n, p, numclasses):
        j = exact.calc_exact(n, p, numclasses)
        print("{:2} {:07.5f}".format(n, j[1]), file=sys.stderr)
        return j

    def permuted(self, items, pieces = 2):
        sublists = [[] for i in range(pieces)]
        for x in items:
            sublists[random.randint(0, pieces - 1)].append(x)
        permutedList = []
        for i in range(pieces):
            time.sleep(0.01)
            random.seed()
            random.shuffle(sublists[i])
            permutedList.extend(sublists[i])
        return permutedList

    def permutations(self, numPerm, aa_classes):
        indices = []
        permStructList = []
        for p in range(numPerm):
            indices.append(self.permuted(aa_classes))
        for index in indices:
            permStruct = FunctionLogo(self.basepairs, exact = self.exact, inverse = self.inverse_exact)
            for i, seqs in enumerate(self.sequences):
                permStruct.add_sequence(index[i], seqs.seq)
            permStructList.append(permStruct)
        return permStructList

    def permute(self, permute_num, proc):
        with Pool(processes = proc) as pool:
            perm_jobs = []
            for x in range(proc):
                if (x == 0):
                    perm_jobs.append((permute_num//proc+permute_num%proc, self.get_functions()))
                else:
                    perm_jobs.append((permute_num//proc, self.get_functions()))

            perm_results = pool.starmap(self.permutations, perm_jobs)
            self.permutationList = []
            for x in perm_results:
                self.permutationList += x

    def permInfo(self, method, proc, inverse = False):
        bp_info = []
        bp_height = []
        single_info = []
        single_height = []
        with Pool(processes = proc) as pool:
            if (not inverse):
                if (method == "NSB"):
                    perm_info_results = pool.map(self.perm_info_calc_NSB, self.permutationList, len(self.permutationList)//proc)
                else:
                    perm_info_results = pool.map(self.perm_info_calc_MM, self.permutationList, len(self.permutationList)//proc)
            else:
                if (method == "NSB"):
                    perm_info_results = pool.map(self.perm_info_calc_inverse_NSB, self.permutationList, len(self.permutationList)//proc)
                else:
                    perm_info_results = pool.map(self.perm_info_calc_inverse_MM, self.permutationList, len(self.permutationList)//proc)

        for perm in perm_info_results:
            bp_info.extend(perm[0])
            single_info.extend(perm[1])
            bp_height.extend(perm[2])
            single_height.extend(perm[3])

        perm_dist = FunctionLogoDist()
        perm_dist.weighted_dist((bp_info, bp_height), (single_info, single_height))
        return perm_dist

    def perm_info_calc_MM(self, x):
        total_info_bp = []
        height_info_bp = []
        total_info_ss = []
        height_info_ss = []
        info, height_dict = x.calculate_entropy_MM()
        for coord in sorted(self.basepairs, key = itemgetter(0)):
            if (coord in info):
                for pairtype in sorted(info[coord]):
                    total_info_bp.append(info[coord][pairtype])
                    for aainfo in sorted(height_dict[coord][pairtype].items(), key = itemgetter(1), reverse = True):
                        height_info_bp.append(aainfo[1]*info[coord][pairtype])

        for coord in range(self.pos):
            if (coord in info):
                for base in sorted(info[coord]):
                    total_info_ss.append(info[coord][base])
                    for aainfo in sorted(height_dict[coord][base].items(), key = itemgetter(1), reverse = True):
                        height_info_ss.append(aainfo[1]*info[coord][base])

        return (total_info_bp, total_info_ss, height_info_bp, height_info_ss)

    def perm_info_calc_inverse_MM(self, x):
        total_info_bp = []
        height_info_bp = []
        total_info_ss = []
        height_info_ss = []
        info, height_dict = x.calculate_entropy_inverse_MM()

        for coord in sorted(self.basepairs, key = itemgetter(0)):
            if (coord in info):
                for pairtype in sorted(info[coord]):
                    total_info_bp.append(info[coord][pairtype])
                    for aainfo in sorted(height_dict[coord][pairtype].items(), key = itemgetter(1), reverse = True):
                        height_info_bp.append(aainfo[1]*info[coord][pairtype])

        for coord in range(self.pos):
            if (coord in info):
                for base in sorted(info[coord]):
                    total_info_ss.append(info[coord][base])
                    for aainfo in sorted(height_dict[coord][base].items(), key = itemgetter(1), reverse = True):
                        height_info_ss.append(aainfo[1]*info[coord][base])

        return (total_info_bp, total_info_ss, height_info_bp, height_info_ss)

    def perm_info_calc_inverse_NSB(self, x):
        total_info_bp = []
        height_info_bp = []
        total_info_ss = []
        height_info_ss = []
        info, height_dict = x.calculate_entropy_inverse_NSB()

        for coord in sorted(self.basepairs, key = itemgetter(0)):
            if (coord in info):
                for pairtype in sorted(info[coord]):
                    total_info_bp.append(info[coord][pairtype])
                    for aainfo in sorted(height_dict[coord][pairtype].items(), key = itemgetter(1), reverse = True):
                        height_info_bp.append(aainfo[1]*info[coord][pairtype])

        for coord in range(self.pos):
            if (coord in info):
                for base in sorted(info[coord]):
                    total_info_ss.append(info[coord][base])
                    for aainfo in sorted(height_dict[coord][base].items(), key = itemgetter(1), reverse = True):
                        height_info_ss.append(aainfo[1]*info[coord][base])

        return (total_info_bp, total_info_ss, height_info_bp, height_info_ss)

    def perm_info_calc_NSB(self, x):
        total_info_bp = []
        height_info_bp = []
        total_info_ss = []
        height_info_ss = []
        info, height_dict = x.calculate_entropy_NSB()

        for coord in sorted(self.basepairs, key = itemgetter(0)):
            if (coord in info):
                for pairtype in sorted(info[coord]):
                    total_info_bp.append(info[coord][pairtype])
                    for aainfo in sorted(height_dict[coord][pairtype].items(), key = itemgetter(1), reverse = True):
                        height_info_bp.append(aainfo[1]*info[coord][pairtype])

        for coord in range(self.pos):
            if (coord in info):
                for base in sorted(info[coord]):
                    total_info_ss.append(info[coord][base])
                    for aainfo in sorted(height_dict[coord][base].items(), key = itemgetter(1), reverse = True):
                        height_info_ss.append(aainfo[1]*info[coord][base])

        return (total_info_bp, total_info_ss, height_info_bp, height_info_ss)

    def calculate_exact(self, n, proc, inverse = False):
        exact_list = []
        if (inverse):
            inverse_functions = Counter()
            for aa_class in self.functions:
                inverse_functions[aa_class] = sum(self.functions.values())/self.functions[aa_class]

            p = [x/sum(list(inverse_functions.values())) for x in inverse_functions.values()]
            for i in range(1,n+1):
                exact_list.append((i, p, len(self.functions.values())))

            print("Calculating Sample Size Correction for Inverse", file = sys.stderr)
            with Pool(processes=proc) as pool:
                exact_results = pool.starmap(self.exact_run, exact_list)

            for x in exact_results:
                self.inverse_exact.append(x[1])
        else:
            p = [x/sum(list(self.functions.values())) for x in self.functions.values()]
            for i in range(1,n+1):
                exact_list.append((i, p, len(self.functions.values())))

            print("Calculating Sample Size Correction", file = sys.stderr)
            with Pool(processes=proc) as pool:
                exact_results = pool.starmap(self.exact_run, exact_list)

            for x in exact_results:
                self.exact.append(x[1])

    def calculate_entropy_MM(self):
        info = defaultdict(lambda : defaultdict(float))
        height_dict = defaultdict(lambda : defaultdict(lambda : defaultdict(float)))

        functions_array = np.array(list(self.functions.values()))
        bg_entropy = -np.sum((functions_array/functions_array.sum()) * np.log2(functions_array/functions_array.sum()))
        for pairs in self.basepairs:
            for state in self.pairs:
                state_counts = self.get(pairs, state)
                if (sum(state_counts.values()) == 0):
                    continue

                fg_entropy = -np.sum((state_counts/state_counts.sum()) * np.log2(state_counts/state_counts.sum()))
                if (sum(state_counts.values()) <= len(self.exact)):
                    expected_bg_entropy = self.exact[sum(state_counts.values()) - 1]
                else:
                    expected_bg_entropy = self.approx_expect(bg_entropy, len(self.functions), sum(state_counts.values()))

                if (expected_bg_entropy-fg_entropy < 0):
                    info[pairs][state] = 0
                else:
                    info[pairs][state] = expected_bg_entropy-fg_entropy

                height_class = {}
                for aa_class in state_counts:
                    height_class[aa_class] = (state_counts[aa_class]/sum(state_counts.values())) / (self.functions[aa_class]/len(self))
                for aa_class in height_class:
                    height_dict[pairs][state][aa_class] = height_class[aa_class]/sum(height_class.values())

        for singles in range(self.pos):
            for state in self.singles:
                state_counts = np.array(list(self.get([singles], state).values()))
                if (state_counts.sum() == 0):
                    continue

                fg_entropy = -np.sum((state_counts/state_counts.sum()) * np.log2(state_counts/state_counts.sum()))
                if (sum(state_counts.values()) <= len(self.exact)):
                    expected_bg_entropy = self.exact[sum(state_counts.values()) - 1]
                else:
                    expected_bg_entropy = self.approx_expect(bg_entropy, len(self.functions), sum(state_counts.values()))

                if (expected_bg_entropy-fg_entropy < 0):
                    info[singles][state] = 0
                else:
                    info[singles][state] = expected_bg_entropy-fg_entropy

                height_class = {}
                for aa_class in state_counts:
                    height_class[aa_class] = (state_counts[aa_class]/sum(state_counts.values())) / (self.functions[aa_class]/len(self))
                for aa_class in height_class:
                    height_dict[singles][state][aa_class] = height_class[aa_class]/sum(height_class.values())

        return (info, height_dict)

    def calculate_entropy_inverse_MM(self):
        info_inverse = defaultdict(lambda : defaultdict(float))
        height_dict_inverse = defaultdict(lambda : defaultdict(lambda : defaultdict(float)))
        inverse_functions = Counter()
        for aa_class in self.functions:
            inverse_functions[aa_class] = sum(self.functions.values())/self.functions[aa_class]

        np_inverse_functions = np.array(list(inverse_functions.values()))
        bg_entropy = -np.sum((np_inverse_functions/np_inverse_functions.sum()) * np.log2(np_inverse_functions/np_inverse_functions.sum()))
        for pairs in self.basepairs:
            for state in self.pairs:
                state_counts = self.get(pairs, state)
                if (sum(state_counts.values()) == 0):
                    continue
                if (not len(state_counts) == len(self.functions)):
                    for function in self.functions:
                        state_counts[function] += 1

                inverse_state_counts = Counter()
                for aa_class in state_counts:
                    inverse_state_counts[aa_class] = sum(state_counts.values())/state_counts[aa_class]

                nsb_array = np.array(list(inverse_state_counts.values()))
                fg_entropy = -np.sum((nsb_array/nsb_array.sum()) * np.log2(nsb_array/nsb_array.sum()))
                #fg_entropy = nb.S(nb.make_nxkx(nsb_array,nsb_array.size), nsb_array.sum(), nsb_array.size)
                if (sum(state_counts.values()) <= len(self.inverse_exact)):
                    expected_bg_entropy = self.inverse_exact[sum(state_counts.values()) - 1]
                else:
                    expected_bg_entropy = self.approx_expect(bg_entropy, len(self.functions), sum(state_counts.values()))

                if (expected_bg_entropy-fg_entropy < 0):
                    info_inverse[pairs][state] = 0
                else:
                    info_inverse[pairs][state] = expected_bg_entropy-fg_entropy

                height_class = {}
                for aa_class in inverse_state_counts:
                    height_class[aa_class] = (inverse_state_counts[aa_class]/sum(inverse_state_counts.values())) / (inverse_functions[aa_class]/sum(inverse_functions.values()))
                for aa_class in height_class:
                    height_dict_inverse[pairs][state][aa_class] = height_class[aa_class]/sum(height_class.values())

        for singles in range(self.pos):
            for state in self.singles:
                state_counts = self.get([singles], state)
                if (sum(state_counts.values()) == 0):
                    continue
                if (not len(state_counts) == len(self.functions)):
                    for function in self.functions:
                        state_counts[function] += 1

                inverse_state_counts = Counter()
                for aa_class in state_counts:
                    inverse_state_counts[aa_class] = sum(state_counts.values())/state_counts[aa_class]

                nsb_array = np.array(list(inverse_state_counts.values()))
                fg_entropy = -np.sum((nsb_array/nsb_array.sum()) * np.log2(nsb_array/nsb_array.sum()))
                if (state_counts.sum() <= len(self.inverse_exact)):
                    expected_bg_entropy = self.inverse_exact[state_counts.sum() -1]
                else:
                    expected_bg_entropy = self.approx_expect(bg_entropy, len(self.functions), state_counts.sum())

                if (expected_bg_entropy-fg_entropy < 0):
                    info_inverse[singles][state] = 0
                else:
                    info_inverse[singles][state] = expected_bg_entropy-fg_entropy

                height_class = {}
                for aa_class in inverse_state_counts:
                    height_class[aa_class] = (inverse_state_counts[aa_class]/sum(inverse_state_counts.values())) / (inverse_functions[aa_class]/sum(inverse_functions.values()))
                for aa_class in height_class:
                    height_dict_inverse[singles][state][aa_class] = height_class[aa_class]/sum(height_class.values())

        return (info_inverse, height_dict_inverse)

    def calculate_entropy_inverse_NSB(self):
        info_inverse = defaultdict(lambda : defaultdict(float))
        height_dict_inverse = defaultdict(lambda : defaultdict(lambda : defaultdict(float)))
        inverse_functions = Counter()
        for aa_class in self.functions:
            inverse_functions[aa_class] = sum(self.functions.values())/self.functions[aa_class]

        np_inverse_functions = np.array(list(inverse_functions.values()))
        bg_entropy = -np.sum((np_inverse_functions/np_inverse_functions.sum()) * np.log2(np_inverse_functions/np_inverse_functions.sum()))
        for pairs in self.basepairs:
            for state in self.pairs:
                state_counts = self.get(pairs, state)
                if (sum(state_counts.values()) == 0):
                    continue
                if (not len(state_counts) == len(self.functions)):
                    for function in self.functions:
                        state_counts[function] += 1

                inverse_state_counts = Counter()
                for aa_class in state_counts:
                    inverse_state_counts[aa_class] = sum(state_counts.values())/state_counts[aa_class]

                nsb_array = np.array(list(inverse_state_counts.values()))
                fg_entropy = nb.S(nb.make_nxkx(nsb_array,nsb_array.size), nsb_array.sum(), nsb_array.size)
                if (sum(state_counts.values()) <= len(self.inverse_exact)):
                    expected_bg_entropy = self.inverse_exact[sum(state_counts.values()) -1]
                else:
                    expected_bg_entropy = bg_entropy

                if (expected_bg_entropy-fg_entropy < 0):
                    info_inverse[pairs][state] = 0
                else:
                    info_inverse[pairs][state] = expected_bg_entropy-fg_entropy

                height_class = {}
                for aa_class in inverse_state_counts:
                    height_class[aa_class] = (inverse_state_counts[aa_class]/sum(inverse_state_counts.values())) / (inverse_functions[aa_class]/sum(inverse_functions.values()))
                for aa_class in height_class:
                    height_dict_inverse[pairs][state][aa_class] = height_class[aa_class]/sum(height_class.values())

        for singles in range(self.pos):
            for state in self.singles:
                state_counts = self.get([singles], state)
                if (sum(state_counts.values()) == 0):
                    continue
                if (not len(state_counts) == len(self.functions)):
                    for function in self.functions:
                        state_counts[function] += 1

                inverse_state_counts = Counter()
                for aa_class in state_counts:
                    inverse_state_counts[aa_class] = sum(state_counts.values())/state_counts[aa_class]

                nsb_array = np.array(list(inverse_state_counts.values()))
                fg_entropy = nb.S(nb.make_nxkx(nsb_array,nsb_array.size), nsb_array.sum(), nsb_array.size)
                if (sum(state_counts.values()) <= len(self.inverse_exact)):
                    expected_bg_entropy = self.inverse_exact[sum(state_counts.values()) - 1]
                else:
                    expected_bg_entropy = bg_entropy

                if (expected_bg_entropy-fg_entropy < 0):
                    info_inverse[singles][state] = 0
                else:
                    info_inverse[singles][state] = expected_bg_entropy-fg_entropy

                height_class = {}
                for aa_class in inverse_state_counts:
                    height_class[aa_class] = (inverse_state_counts[aa_class]/sum(inverse_state_counts.values())) / (inverse_functions[aa_class]/sum(inverse_functions.values()))
                for aa_class in height_class:
                    height_dict_inverse[singles][state][aa_class] = height_class[aa_class]/sum(height_class.values())

        return (info_inverse, height_dict_inverse)

    def calculate_entropy_NSB(self):
        info = defaultdict(lambda : defaultdict(float))
        height_dict = defaultdict(lambda : defaultdict(lambda : defaultdict(float)))

        functions_array = np.array(list(self.functions.values()))
        bg_entropy = -np.sum((functions_array/functions_array.sum()) * np.log2(functions_array/functions_array.sum()))
        for pairs in self.basepairs:
            for state in self.pairs:
                state_counts = self.get(pairs, state)
                if (sum(state_counts.values()) == 0):
                    continue
                nsb_array = np.array(list(state_counts.values()) + [0]*(len(self.functions) - len(state_counts)))
                fg_entropy = nb.S(nb.make_nxkx(nsb_array,nsb_array.size), nsb_array.sum(), nsb_array.size)
                if (sum(state_counts.values()) <= len(self.exact)):
                    expected_bg_entropy = self.exact[sum(state_counts.values()) - 1]
                else:
                    expected_bg_entropy = bg_entropy

                if (expected_bg_entropy-fg_entropy < 0):
                    info[pairs][state] = 0
                else:
                    info[pairs][state] = expected_bg_entropy-fg_entropy

                height_class = {}
                for aa_class in state_counts:
                    height_class[aa_class] = (state_counts[aa_class]/sum(state_counts.values())) / (self.functions[aa_class]/len(self))
                for aa_class in height_class:
                    height_dict[pairs][state][aa_class] = height_class[aa_class]/sum(height_class.values())

        for singles in range(self.pos):
            for state in self.singles:
                state_counts = self.get([singles], state)
                if (sum(state_counts.values()) == 0):
                    continue
                nsb_array = np.array(list(state_counts.values()) + [0]*(len(self.functions) - len(state_counts)))
                fg_entropy = nb.S(nb.make_nxkx(nsb_array,nsb_array.size), nsb_array.sum(), nsb_array.size)
                if (sum(state_counts.values()) <= len(self.exact)):
                    expected_bg_entropy = self.exact[sum(state_counts.values()) - 1]
                else:
                    expected_bg_entropy = bg_entropy

                if (expected_bg_entropy-fg_entropy < 0):
                    info[singles][state] = 0
                else:
                    info[singles][state] = expected_bg_entropy-fg_entropy

                height_class = {}
                for aa_class in state_counts:
                    height_class[aa_class] = (state_counts[aa_class]/sum(state_counts.values())) / (self.functions[aa_class]/len(self))
                for aa_class in height_class:
                    height_dict[singles][state][aa_class] = height_class[aa_class]/sum(height_class.values())

        return (info, height_dict)



    def is_overlap(self, position):
        pass

    def add_sequence(self, function, seq):
        self.sequences.append(Seq(function, seq))
        self.functions[function] += 1
        self.pos = len(seq)
        self.singles.update(seq)
        for x in self.basepairs:
            self.pairs.add(seq[x[0]] +  seq[x[1]])

    def get(self, position, state):
        ret_counter = Counter()
        if (len(position) == 1):
            for x in self.sequences:
                if (x.seq[position[0]] == state[0]):
                    ret_counter[x.function] += 1
        if (len(position) == 2):
            for x in self.sequences:
                if (x.seq[position[0]] == state[0] and x.seq[position[1]] == state[1]):
                    ret_counter[x.function] += 1

        return ret_counter

    def get_functions(self):
        function_list = []
        for key, val in self.functions.items():
            function_list.extend([key]*val)
        return function_list

    def __len__(self):
        return len(self.sequences)