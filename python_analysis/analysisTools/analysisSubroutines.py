from __future__ import with_statement
import coffea
from coffea.nanoevents import NanoEventsFactory, NanoAODSchema, BaseSchema
from coffea import processor
import coffea.hist as hist
from coffea.nanoevents.methods import vector
import uproot
import awkward as ak
ak.behavior.update(vector.behavior)
import numpy as np
import matplotlib.pyplot as plt
import json
import os
import time
import importlib
import pandas as pd
from XRootD import client
NanoAODSchema.warn_missing_crossrefs = False

# Routines to produce additional variables (e.g. best vertex, good electrons, etc) for cuts
# These are produced every time the analyzer is run
def selectGoodElesAndVertices(events):
    # Selecting electrons that pass basic pT and eta cuts
    eles = events.Electron
    ele_idx = ak.local_index(eles)
    lpt_eles = events.LptElectron
    lpt_ele_idx = ak.local_index(lpt_eles)

    good_ele_msk = (eles.pt > 1) & (np.abs(eles.eta) < 2.4)
    good_lpt_ele_msk = (lpt_eles.pt > 1) & (np.abs(lpt_eles.eta) < 2.4)

    good_eles = eles[good_ele_msk]
    good_ele_idx = ele_idx[good_ele_msk]
    good_eles.__setitem__("idx",good_ele_idx)

    good_lpt_eles = lpt_eles[good_lpt_ele_msk]
    good_lpt_ele_idx = lpt_ele_idx[good_lpt_ele_msk]
    good_lpt_eles.__setitem__("idx",good_lpt_ele_idx)

    events.__setitem__("good_ele",good_eles)
    events.__setitem__("good_lpt_ele",good_lpt_eles)

    # Selecting vertices corresponding to good electrons
    RRvtx = events.RRvtx
    LRvtx = events.LRvtx
    LLvtx = events.LLvtx
    
    goodRR_msk = ak.any(RRvtx.idx1 == good_eles.idx[:,np.newaxis,:],axis=-1) & ak.any(RRvtx.idx2 == good_eles.idx[:,np.newaxis,:],axis=-1)
    goodLR_msk = ak.any(LRvtx.idx1 == good_lpt_eles.idx[:,np.newaxis,:],axis=-1) & ak.any(LRvtx.idx2 == good_eles.idx[:,np.newaxis,:],axis=-1)
    goodLL_msk = ak.any(LLvtx.idx1 == good_lpt_eles.idx[:,np.newaxis,:],axis=-1) & ak.any(LLvtx.idx2 == good_lpt_eles.idx[:,np.newaxis,:],axis=-1)

    events.__setitem__("good_RRvtx",RRvtx[goodRR_msk])
    events.__setitem__("good_LRvtx",LRvtx[goodLR_msk])
    events.__setitem__("good_LLvtx",LLvtx[goodLL_msk])

def selectBestVertex(events):
    RR = events.good_RRvtx[ak.argmin(events.good_RRvtx.reduced_chi2,axis=1,keepdims=True)]
    LR = events.good_LRvtx[ak.argmin(events.good_LRvtx.reduced_chi2,axis=1,keepdims=True)]
    LL = events.good_LLvtx[ak.argmin(events.good_LLvtx.reduced_chi2,axis=1,keepdims=True)]

    allVtx = ak.concatenate((RR,LR,LL),axis=1)
    vtxType = ak.concatenate([ak.ones_like(RR.idx1),2*ak.ones_like(LR.idx1),3*ak.ones_like(LL.idx1)],axis=1)
    best = ak.argmin(allVtx.reduced_chi2,axis=1,keepdims=True)
    bestVertices = allVtx[best]
    bestVertices.__setitem__("vtxType",vtxType[best])

    sel_e1 = ak.where(bestVertices.vtxType[:,0]==1, events.Electron, events.LptElectron)
    sel_e2 = ak.where(bestVertices.vtxType[:,0]==3, events.LptElectron, events.Electron)

    sel_e1 = sel_e1[bestVertices.idx1]
    sel_e2 = sel_e2[bestVertices.idx2]

    events.__setitem__("sel_vtx",bestVertices[:,0])
    events.__setitem__("sel_e1",sel_e1[:,0])
    events.__setitem__("sel_e2",sel_e2[:,0])

# Specialized routines to create variables for particular histograms
# Must specify which ones you want to run in the histogram config (will need to run the ones that make the vars for your histograms)

def eleVtxGenMatching(events):
    # Electron collections
    ele = events.Electron
    lpt_ele = events.LptElectron
    cand_ele = events.EleCand
    gen_ele = events.GenEle
    gen_pos = events.GenPos

    # Electron gen-matches
    ele_matches = events.GenEleMatches
    pos_matches = events.GenPosMatches
    ele_match = events.GenEleMatch
    pos_match = events.GenPosMatch
    ele_matchC = events.GenEleMatchC
    pos_matchC = events.GenPosMatchC

    # Find unique matches with different collections / uniqueness schemes
    ematch, pmatch = findUniqueMatches(ele_matches,ele_match,pos_matches,pos_match)
    ematch11, pmatch11 = findUniqueMatches(ele_matches,ele_match,pos_matches,pos_match,allow11=True)
    ematchC, pmatchC = findUniqueMatches(ele_matches,ele_matchC,pos_matches,pos_matchC,useCands=True)
    ematchC11, pmatchC11 = findUniqueMatches(ele_matches,ele_matchC,pos_matches,pos_matchC,allow11=True,useCands=True)

    events.__setitem__("ematch",ematch)
    events.__setitem__("pmatch",pmatch)
    events.__setitem__("ematch11",ematch11)
    events.__setitem__("pmatch11",pmatch11)
    events.__setitem__("ematchC",ematchC)
    events.__setitem__("pmatchC",pmatchC)
    events.__setitem__("ematchC11",ematchC11)
    events.__setitem__("pmatchC11",pmatchC11)

    #####################################
    ####### VERTEX MATCHING STUFF #######
    #####################################

    # masks for different vertex match types, low/reg only
    noMatch_RL = (ematch.typ == 0) & (pmatch.typ == 0)
    matchRR_RL = (ematch.typ == 1) & (pmatch.typ == 1)
    matchLR_RL = ((ematch.typ == 1) & (pmatch.typ == 2)) | ((ematch.typ == 2) & (pmatch.typ == 1))
    matchLL_RL = (ematch.typ == 2) & (pmatch.typ == 2)
    ones = ak.ones_like(ematch.typ)
    zeros = ak.zeros_like(ematch.typ)
    matchType_RL = ak.where(noMatch_RL,zeros,-1*ones)
    matchType_RL = ak.where(matchRR_RL,ones,matchType_RL)
    matchType_RL = ak.where(matchLR_RL,2*ones,matchType_RL)
    matchType_RL = ak.where(matchLL_RL,3*ones,matchType_RL)

    events.__setitem__("eeMatchRR_RL",matchRR_RL)
    events.__setitem__("eeMatchLR_RL",matchLR_RL)
    events.__setitem__("eeMatchLL_RL",matchLL_RL)
    events.__setitem__("eeMatchType_RL",matchType_RL)

    # masks for different vertex match types, low/reg/cand
    noMatch_RLC = (ematchC.typ == 0) & (pmatchC.typ == 0)
    matchRR_RLC = (ematchC.typ == 1) & (pmatchC.typ == 1)
    matchRC_RLC = ((ematchC.typ == 1) & (pmatchC.typ == 3)) | ((ematchC.typ == 3) & (pmatchC.typ == 1))
    matchLR_RLC = ((ematchC.typ == 1) & (pmatchC.typ == 2)) | ((ematchC.typ == 2) & (pmatchC.typ == 1))
    matchLC_RLC = ((ematchC.typ == 2) & (pmatchC.typ == 3)) | ((ematchC.typ == 3) & (pmatchC.typ == 2))
    matchLL_RLC = (ematchC.typ == 2) & (pmatchC.typ == 2)
    matchCC_RLC = (ematchC.typ == 3) & (pmatchC.typ == 3)
    ones = ak.ones_like(ematchC.typ)
    zeros = ak.zeros_like(ematchC.typ)
    matchType_RLC = ak.where(noMatch_RLC,zeros,-1*ones)
    matchType_RLC = ak.where(matchRR_RLC,ones,matchType_RLC)
    matchType_RLC = ak.where(matchLR_RLC,2*ones,matchType_RLC)
    matchType_RLC = ak.where(matchLL_RLC,3*ones,matchType_RLC)
    matchType_RLC = ak.where(matchRC_RLC,4*ones,matchType_RLC)
    matchType_RLC = ak.where(matchLC_RLC,5*ones,matchType_RLC)
    matchType_RLC = ak.where(matchCC_RLC,6*ones,matchType_RLC)

    events.__setitem__("eeMatchRR_RLC",matchRR_RLC)
    events.__setitem__("eeMatchRC_RLC",matchRC_RLC)
    events.__setitem__("eeMatchLR_RLC",matchLR_RLC)
    events.__setitem__("eeMatchLC_RLC",matchLC_RLC)
    events.__setitem__("eeMatchLL_RLC",matchLL_RLC)
    events.__setitem__("eeMatchCC_RLC",matchCC_RLC)
    events.__setitem__("eeMatchType_RLC",matchType_RLC)

    #######################################
    ####### ELECTRON MATCHING STUFF #######
    #######################################
    # calculating other useful quantities
    nEmatch = ak.count(ele_matches[ele_matches.typ != 3].dr,axis=1)
    nPmatch = ak.count(pos_matches[pos_matches.typ != 3].dr,axis=1)
    nEmatchC = ak.count(ele_matches.dr,axis=1)
    nPmatchC = ak.count(pos_matches.dr,axis=1)

    events.__setitem__("nEmatch",nEmatch)
    events.__setitem__("nPmatch",nPmatch)
    events.__setitem__("nEmatchC",nEmatchC)
    events.__setitem__("nPmatchC",nPmatchC)

    # determining e+e- "match classes" for each event
    zeros = ak.zeros_like(ematch.typ) # generic vector of zeros for each event
    ones = ak.ones_like(ematch.typ) # generic vector fo ones for each event
    
    noMatch = (ematch11.typ == 0) & (pmatch11.typ == 0)
    oneMatch = ((ematch11.typ != 0) & (pmatch11.typ == 0)) | ((ematch11.typ == 0) & (pmatch11.typ != 0))
    degenMatch = (ematch11.typ != 0) & (pmatch11.typ != 0) & ((ematch11.typ == pmatch11.typ) & (ematch11.ind == pmatch11.ind))
    uniqMatch = (ematch11.typ != 0) & (pmatch11.typ != 0) & ((ematch11.typ != pmatch11.typ) | (ematch11.ind != pmatch11.ind))
    matchClass = ak.where(noMatch,zeros,-1*ones)
    matchClass = ak.where(oneMatch,ones,matchClass)
    matchClass = ak.where(degenMatch,2*ones,matchClass)
    matchClass = ak.where(uniqMatch,3*ones,matchClass)

    events.__setitem__("eleMatchClass",matchClass)

    noMatchC = (ematchC11.typ == 0) & (pmatchC11.typ == 0)
    oneMatchC = ((ematchC11.typ != 0) & (pmatchC11.typ == 0)) | ((ematchC11.typ == 0) & (pmatchC11.typ != 0))
    degenMatchC = (ematchC11.typ != 0) & (pmatchC11.typ != 0) & ((ematchC11.typ == pmatchC11.typ) & (ematchC11.ind == pmatchC11.ind))
    uniqMatchC = (ematchC11.typ != 0) & (pmatchC11.typ != 0) & ((ematchC11.typ != pmatchC11.typ) | (ematchC11.ind != pmatchC11.ind))
    matchClassC = ak.where(noMatchC,zeros,-1*ones)
    matchClassC = ak.where(oneMatchC,ones,matchClassC)
    matchClassC = ak.where(degenMatchC,2*ones,matchClassC)
    matchClassC = ak.where(uniqMatchC,3*ones,matchClassC)

    events.__setitem__("eleMatchClassC",matchClassC)
    
def genParticles(events):
    gen_eles = ak.concatenate([events.GenEle,events.GenPos])
    gen_ele = events.GenEle
    gen_pos = events.GenPos
    ee = events.genEE

    """histos['ele_kinematics'].fill(sample=samp,cut=cut,ele_type="Generator",
                        pt=gen_eles.pt,eta=gen_eles.eta,phi=gen_eles.phi)
    histos['gen_displacement'].fill(sample=samp,cut=cut,
                        vxy=gen_eles.vxy,
                        vz=gen_eles.vz)
    histos["gen_ee_kinematics"].fill(sample=samp,cut=cut,
                mass=ee.mass,
                dR=ee.dr)"""

def conversions(events,histos,samp,cut):
    eles = events.Electron
    lpt_eles = events.LptElectron
    convs = events.Conversion
    gen_eles = events.GenPart[np.abs(events.GenPart.ID) == 11]
    gen_ele = ak.flatten(events.GenPart[events.GenPart.ID == 11])
    gen_pos = ak.flatten(events.GenPart[events.GenPart.ID == -11])

    eles_dir = ak.zip(
        {
            "x":eles.eta,
            "y":eles.phi
        },
        with_name="TwoVector"
    )
    lpt_eles_dir = ak.zip(
        {
            "x":lpt_eles.eta,
            "y":lpt_eles.phi
        },
        with_name="TwoVector"
    )
    conv1_dir = ak.zip(
        {
            "x":convs.trk1_innerEta,
            "y":convs.trk1_innerPhi,
        },
        with_name="TwoVector"
    )
    conv2_dir = ak.zip(
        {
            "x":convs.trk2_innerEta,
            "y":convs.trk2_innerPhi,
        },
        with_name="TwoVector"
    )
    gen_ele_dir = ak.zip(
        {
            "x":gen_ele.eta,
            "y":gen_ele.phi,
        },
        with_name="TwoVector"
    )
    gen_pos_dir = ak.zip(
        {
            "x":gen_pos.eta,
            "y":gen_pos.phi,
        },
        with_name="TwoVector"
    )

    all_eles_dir = ak.concatenate([eles_dir,lpt_eles_dir,conv1_dir,conv2_dir],axis=1)
    all_eles_labels = ak.concatenate([ak.ones_like(eles.eta),2*ak.ones_like(lpt_eles.eta),
                                        3*ak.ones_like(convs.trk1_innerEta),3*ak.ones_like(convs.trk2_innerEta)],axis=1)

    dR_e = (all_eles_dir - gen_ele_dir).r
    dR_p = (all_eles_dir - gen_pos_dir).r
    nearest_e = ak.argmin(dR_e,axis=1,keepdims=True)
    nearest_p = ak.argmin(dR_p,axis=1,keepdims=True)
    mindR_e = ak.fill_none(ak.flatten(dR_e[nearest_e]),999)
    mindR_p = ak.fill_none(ak.flatten(dR_p[nearest_p]),999)
    type_e_nearest = ak.fill_none(ak.flatten(all_eles_labels[nearest_e]),0)
    type_p_nearest = ak.fill_none(ak.flatten(all_eles_labels[nearest_p]),0)
    
    match_e = mindR_e < 0.1
    match_p = mindR_p < 0.1
    type_e_nearest = type_e_nearest*ak.values_astype(match_e,int) # sets match type to 0 (no match) where dR < 0.1 criterion not satisfied
    type_p_nearest = type_p_nearest*ak.values_astype(match_p,int)
    histos['match_matrix'].fill(sample=samp,
                    e_matchType=type_e_nearest,
                    p_matchType=type_p_nearest)

    ## Conversion-specific studies
    d1e = (conv1_dir - gen_ele_dir).r
    d1p = (conv1_dir - gen_pos_dir).r
    d2e = (conv2_dir - gen_ele_dir).r
    d2p = (conv2_dir - gen_pos_dir).r
    ## Matching to most nearby gen object (possible for both conv eles matched to same object)
    d1e_min = ak.fill_none(ak.flatten(d1e[ak.argmin(d1e,axis=1,keepdims=True)]),999)
    d1p_min = ak.fill_none(ak.flatten(d1p[ak.argmin(d1p,axis=1,keepdims=True)]),999)
    d2e_min = ak.fill_none(ak.flatten(d2e[ak.argmin(d2e,axis=1,keepdims=True)]),999)
    d2p_min = ak.fill_none(ak.flatten(d2p[ak.argmin(d2p,axis=1,keepdims=True)]),999)
    matchType_conv1 = ak.values_astype(d1e_min<0.1,int) + 2*ak.values_astype(d1p_min<0.1,int) #0 if no match, 1 if match to e, 2 if match to p, 3 if match to both
    matchType_conv2 = ak.values_astype(d2e_min<0.1,int) + 2*ak.values_astype(d2p_min<0.1,int)
    fullUniqMatch = ((matchType_conv1 == 1) & (matchType_conv2 == 2)) | ((matchType_conv1 == 2) & (matchType_conv2 == 1))
    fullMatch = (matchType_conv1 > 0) & (matchType_conv2 > 0)
    anyMatch = (matchType_conv1 > 0) | (matchType_conv2 > 0)
    histos['conv_match_matrix'].fill(sample=samp,cut=cut,
                        match="all",
                        c1_matchType=matchType_conv1,
                        c2_matchType=matchType_conv2)
    histos['conv_match_matrix'].fill(sample=samp,cut=cut,
                        match="fullUnique",
                        c1_matchType=matchType_conv1[fullUniqMatch],
                        c2_matchType=matchType_conv2[fullUniqMatch])
    histos['conv_match_matrix'].fill(sample=samp,cut=cut,
                        match="full",
                        c1_matchType=matchType_conv1[fullMatch],
                        c2_matchType=matchType_conv2[fullMatch])
    histos['conv_match_matrix'].fill(sample=samp,cut=cut,
                        match="any",
                        c1_matchType=matchType_conv1[anyMatch],
                        c2_matchType=matchType_conv2[anyMatch])
    ## Attempting un-ambiguous matches - i.e. "best" matches
    ## If e.g. both conv electrons are best matched to the same object, but one is *better* matched and the 
    ## other could also be matched to the other gen object, just not as well
    both_c1 = (matchType_conv1 == 3)
    both_c2 = (matchType_conv2 == 3)
    # zeroing out the "both" matches
    uniqMatch_conv1 = matchType_conv1*ak.values_astype(~both_c1,int)
    uniqMatch_conv2 = matchType_conv2*ak.values_astype(~both_c2,int)
    # setting to 1 or 2 based on smaller dR, only where there was a "both" match
    uniqMatch_conv1 = uniqMatch_conv1 + ak.values_astype(both_c1,int)*(ak.values_astype(d1e_min < d1p_min,int) + 2*ak.values_astype(d1e_min > d1p_min,int))
    uniqMatch_conv2  = uniqMatch_conv2 + ak.values_astype(both_c2,int)*(ak.values_astype(d2e_min < d2p_min,int) + 2*ak.values_astype(d2e_min > d2p_min,int))
    # Disambiguate some "double" matches -- e.g. conv1 and conv2 both matched to same gen object
    c1c2_e = (uniqMatch_conv1 == uniqMatch_conv2) & (uniqMatch_conv1 == 1)
    c1c2_p = (uniqMatch_conv1 == uniqMatch_conv2) & (uniqMatch_conv1 == 2)
    # zeroing out the "double" matches
    oldMatch_conv1 = 1*uniqMatch_conv1
    oldMatch_conv2 = 1*uniqMatch_conv2
    uniqMatch_conv1 = uniqMatch_conv1*ak.values_astype(~c1c2_e,int)*ak.values_astype(~c1c2_p,int)
    uniqMatch_conv2 = uniqMatch_conv2*ak.values_astype(~c1c2_e,int)*ak.values_astype(~c1c2_p,int)
    # When c1 and c2 are matched to the same object, see if there's a distinct matching possible instead
    switch1_e2p = (c1c2_e) & (d1p_min < 0.1) & ( (d1e_min >= d2e_min) | (d2p_min > 0.1) )
    switch1_p2e = (c1c2_p) & (d1e_min < 0.1) & ( (d1p_min >= d2p_min) | (d2e_min > 0.1) )
    switch2_e2p = (c1c2_e) & (d2p_min < 0.1) & ( (d2e_min > d1e_min) | (d1p_min > 0.1) )
    switch2_p2e = (c1c2_p) & (d2e_min < 0.1) & ( (d2p_min > d1p_min) | (d1e_min > 0.1) )
    no_switch1 = (c1c2_e & (~switch1_e2p)) | (c1c2_p & (~switch1_p2e))
    no_switch2 = (c1c2_e & (~switch2_e2p)) | (c1c2_p & (~switch2_p2e))
    uniqMatch_conv1 = uniqMatch_conv1 + ak.values_astype(switch1_p2e,int) + 2*ak.values_astype(switch1_e2p,int) + oldMatch_conv1*ak.values_astype(no_switch1,int)
    uniqMatch_conv2 = uniqMatch_conv2 + ak.values_astype(switch2_p2e,int) + 2*ak.values_astype(switch2_e2p,int) + oldMatch_conv2*ak.values_astype(no_switch2,int)

    histos['conv_match_matrix_uniq'].fill(sample=samp,cut=cut,
                                match="all",
                                c1_matchType=uniqMatch_conv1,
                                c2_matchType=uniqMatch_conv2)
    histos['conv_match_matrix_uniq'].fill(sample=samp,cut=cut,
                                match="full",
                                c1_matchType=uniqMatch_conv1[fullMatch],
                                c2_matchType=uniqMatch_conv2[fullMatch])
    histos['conv_match_matrix_uniq'].fill(sample=samp,cut=cut,
                                match="any",
                                c1_matchType=uniqMatch_conv1[anyMatch],
                                c2_matchType=uniqMatch_conv2[anyMatch])

# Helper functions for other routines
def findNearestReco(gen,reco,types,thresh=0.1):
    # construct eta-phi vectors
    gen_r = ak.zip({"x":gen.eta,"y":gen.phi},with_name="TwoVector")
    reco_r = ak.zip({"x":reco.eta,"y":reco.phi},with_name="TwoVector")
    # compute dRs
    dr = (reco_r - gen_r).r  
    # sort by ascending dR
    isort = ak.argsort(dr,axis=1)
    dr = dr[isort]
    types = types[isort]
    # keep only matches with dR < threshold
    match = dr < thresh
    dr = dr[match]
    types = types[match]
    imatch = isort[match] 

    return imatch, types, dr

def findMatches(gen1,gen2,reco,recoType):
    i1, t1, dr1 = findNearestReco(gen1,reco,recoType)
    i2, t2, dr2 = findNearestReco(gen2,reco,recoType)
    return i1, t1, dr1, i2, t2, dr2

def findUniqueMatches(ele_matches,best_ele_match,pos_matches,best_pos_match,useCands=False,allow11=False):
    if not useCands:
        ele_matches = ele_matches[ele_matches.typ != 3]
        pos_matches = pos_matches[pos_matches.typ != 3]
    numE = ak.count(ele_matches.typ,axis=1)
    numP = ak.count(pos_matches.typ,axis=1)
    idx = ak.Array(np.arange(len(best_ele_match)))

    partitions = []
    ele = []
    pos = []

    for i in range(1):
        # removing events where one or more objects has no match
        cutA = (numE > 0) & (numP > 0)
        ele.append(best_ele_match[~cutA])
        pos.append(best_pos_match[~cutA])
        partitions.append(idx[~cutA])
        ele_matches = ele_matches[cutA]
        best_ele_match = best_ele_match[cutA]
        pos_matches = pos_matches[cutA]
        best_pos_match = best_pos_match[cutA]
        idx = idx[cutA]
        numE = numE[cutA]
        numP = numP[cutA]

        if len(numE) == 0:
            break

        # remove events with distinct match
        cutB = (best_ele_match.typ == best_pos_match.typ) & (best_ele_match.ind == best_pos_match.ind)
        ele.append(best_ele_match[~cutB])
        pos.append(best_pos_match[~cutB])
        partitions.append(idx[~cutB])
        ele_matches = ele_matches[cutB]
        best_ele_match = best_ele_match[cutB]
        pos_matches = pos_matches[cutB]
        best_pos_match = best_pos_match[cutB]
        idx = idx[cutB]
        numE = numE[cutB]
        numP = numP[cutB]

        if len(numP) == 0:
            break

        # sorting remaining matches by dR
        sort_ele = ak.argsort(ele_matches.dr,axis=1)
        sort_pos = ak.argsort(pos_matches.dr,axis=1)
        ele_matches = ele_matches[sort_ele]
        pos_matches = pos_matches[sort_pos]
        
        cutC = (numE == 1) & (numP == 1)
        cutD = (numE >= 2) & (numP == 1)
        cutE = (numE == 1) & (numP >= 2)
        cutF = (numE >= 2) & (numP >= 2)

        if ak.count_nonzero(cutC) > 0:
            ele_best = best_ele_match[cutC]
            pos_best = best_pos_match[cutC]
            if not allow11:
                ele_best = ak.where(ele_best.dr < pos_best.dr,ele_best,ak.full_like(ele_best,0))
                pos_best = ak.where(pos_best.dr < ele_best.dr,pos_best,ak.full_like(pos_best,0))
            ele.append(ele_best)
            pos.append(pos_best)
            partitions.append(idx[cutC])
        if ak.count_nonzero(cutD) > 0:
            ele_best = ele_matches[cutD][:,1]
            pos_best = best_pos_match[cutD]
            ele.append(ele_best)
            pos.append(pos_best)
            partitions.append(idx[cutD])
        if ak.count_nonzero(cutE) > 0:
            ele_best = best_ele_match[cutE]
            pos_best = pos_matches[cutE][:,1]
            ele.append(ele_best)
            pos.append(pos_best)
            partitions.append(idx[cutE])
        if ak.count_nonzero(cutF) > 0:
            ele_best = ak.where(best_ele_match[cutF].dr < best_pos_match[cutF].dr,ele_matches[cutF][:,0],ele_matches[cutF][:,1])
            pos_best = ak.where(best_pos_match[cutF].dr < best_ele_match[cutF].dr,pos_matches[cutF][:,0],pos_matches[cutF][:,1])
            ele.append(ele_best)
            pos.append(pos_best)
            partitions.append(idx[cutF])
    
    all_partitions = ak.concatenate(partitions)
    reorder = ak.argsort(all_partitions)
    ele_out = ak.concatenate(ele)[reorder]
    pos_out = ak.concatenate(pos)[reorder]

    return ele_out, pos_out
