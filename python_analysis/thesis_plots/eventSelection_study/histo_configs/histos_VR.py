import numpy as np
import awkward as ak
from myHisto import myHisto

def make_histograms(info):
    h = myHisto()
    h.make("sel_e1e2_type",("e1type",["L","R"]),("e2type",["L","R"]))
    
    # selected vertex
    h.make("sel_vtx_dR",'dR')
    h.make("sel_vtx_corrdR",'dR')
    h.make("sel_vtx_dR_lo",'dR_lo')
    h.make("sel_vtx_corrdR_lo",'dR_lo')
    h.make("sel_vtx_mindxy",'dxy')
    h.make("sel_vtx_corrMindxy",'dxy')
    h.make("sel_vtx_vxy1",'vxy1')
    h.make("sel_vtx_vxy10",'vxy10')
    h.make("sel_vtx_vxy100",'vxy100')
    h.make("sel_vtx_leadpT",'ele_pt')
    h.make("sel_vtx_METdPhi",'abs_dphi')
    h.make("sel_vtx_mindRj",'dR')
    h.make("sel_vtx_chi2",'vtx_chi2')
    h.make('sel_vtx_mass','vtx_mass')
    h.make('sel_vtx_corrMass','vtx_mass')
    h.make("sel_vtx_mass_low",'mass_low')
    h.make("sel_vtx_corrMass_low",'mass_low')
    h.make("sel_vtx_mass_long",'vtx_mass_long')
    h.make("sel_vtx_corrMass_long",'vtx_mass_long')
    h.make('sel_vtx_mass_high','vtx_mass_high')
    h.make('sel_vtx_corrMass_high','vtx_mass_high')
    h.make('sel_vtx_mindPhiJ','abs_dphi')
    h.make('sel_vtx_sign','vtx_sign')
    h.make('sel_vtx_pt','vtx_pt')
    h.make('sel_vtx_corrPt','vtx_pt')
    h.make('sel_vtx_eta','eta')
    h.make('sel_vtx_corrEta','eta')
    h.make('sel_vtx_phi','phi')
    h.make('sel_vtx_corrPhi','phi')
    h.make("sel_vtx_type",'vtx_type')
    h.make("sel_vtx_minEleDrJ",'dR')
    h.make("sel_vtx_minEleDPhiJ",'abs_dphi')
    h.make("sel_vtx_mindxy_low",'mindxy_low')
    h.make("sel_vtx_corrMindxy_low",'mindxy_low')
    h.make("sel_vtx_sign_etaProd",'sign_etaProd')
    h.make("sel_vtx_CosThetaColl",'cosTheta')
    h.make("sel_vtx_LxyCosThetaColl",'LxyCosTheta')
    h.make("sel_vtx_LxyCosThetaCollZoom",'LxyCosThetaZoom')
    h.make("sel_vtx_LxyCosThetaCollZoomZoom",'LxyCosThetaZoomZoom')
    h.make("sel_vtx_CorrCosThetaColl",'cosTheta')
    h.make("sel_vtx_CorrLxyCosThetaColl",'LxyCosTheta')
    h.make("sel_vtx_CorrLxyCosThetaCollZoom",'LxyCosThetaZoom')
    h.make("sel_vtx_CorrLxyCosThetaCollZoomZoom",'LxyCosThetaZoomZoom')
    h.make("sel_vtx_eleDphi",'abs_dphi')
    h.make("sel_vtx_maxMiniRelIso",'iso')
    h.make("sel_vtx_maxMiniRelIsoCorr",'iso')
    h.make("sel_vtx_e1e2PassConvVeto",'passConvVeto')
    
    h.make("sel_vtx_vxyRes","vxyRes")
    h.make("sel_vtx_vxySignif","vxySignif")
    
    # misc other quantities
    h.make("PFMET",'met')
    h.make("jetMETdPhi",'abs_dphi')
    h.make("minJetMETdPhi",'abs_dphi')
    h.make("nJets",'nJets')
    h.make('lead_jet_pt','jet_pt')
    h.make('lead_jet_eta','eta')
    h.make("jetMETratio",'jetMETratio')
    h.make("pfCalo_metRatio",'met_ratio')
    
    if info['type'] == 'signal':
        h.make("selMatch_vs_hasMatch",'match','match_exist')

    return h

subroutines = []

def fillHistos(events,h,samp,cut,info,sum_wgt=1):
    h.samp = samp
    h.cut = cut
    if info["type"] == "signal" or info["type"] == "bkg":
        wgt = events.eventWgt/sum_wgt
    else:
        wgt = 1

    sel_vtx = events.sel_vtx
    ### FILLING HISTOGRAMS ###
    h.fill("sel_e1e2_type",e1type=sel_vtx.e1_typ,e2type=sel_vtx.e2_typ,weight=wgt)

    #
    h.fill("sel_vtx_dR",dR=sel_vtx.dR,weight=wgt)
    h.fill("sel_vtx_corrdR",dR=sel_vtx.refit_dR,weight=wgt)
    h.fill("sel_vtx_dR_lo",dR=sel_vtx.dR,weight=wgt)
    h.fill("sel_vtx_corrdR_lo",dR=sel_vtx.refit_dR,weight=wgt)
    h.fill("sel_vtx_mindxy",dxy=sel_vtx.min_dxy,weight=wgt)
    h.fill("sel_vtx_corrMindxy",dxy=sel_vtx.corrMinDxy,weight=wgt)
    h.fill("sel_vtx_vxy1",vxy=sel_vtx.vxy,weight=wgt)
    h.fill("sel_vtx_vxy10",vxy=sel_vtx.vxy,weight=wgt)
    h.fill("sel_vtx_vxy100",vxy=sel_vtx.vxy,weight=wgt)
    h.fill("sel_vtx_leadpT",pt=np.maximum(sel_vtx.e1.pt,sel_vtx.e2.pt),weight=wgt)
    h.fill("sel_vtx_METdPhi",abs_dphi=np.abs(sel_vtx.METdPhi),weight=wgt)
    h.fill('sel_vtx_mindRj',dR=sel_vtx.mindRj,weight=wgt)
    h.fill('sel_vtx_chi2',chi2=sel_vtx.reduced_chi2,weight=wgt)
    h.fill('sel_vtx_mass',mass=sel_vtx.m,weight=wgt)
    h.fill('sel_vtx_corrMass',mass=sel_vtx.refit_m,weight=wgt)
    h.fill("sel_vtx_mass_low",mass_low=sel_vtx.m,weight=wgt)
    h.fill("sel_vtx_corrMass_low",mass_low=sel_vtx.refit_m,weight=wgt)
    h.fill("sel_vtx_mass_long",mass=sel_vtx.m,weight=wgt)
    h.fill("sel_vtx_corrMass_long",mass=sel_vtx.refit_m,weight=wgt)
    h.fill("sel_vtx_mass_high",mass=sel_vtx.m,weight=wgt)
    h.fill("sel_vtx_corrMass_high",mass=sel_vtx.refit_m,weight=wgt)
    h.fill('sel_vtx_mindPhiJ',abs_dphi=np.abs(sel_vtx.mindPhiJ),weight=wgt)
    h.fill('sel_vtx_sign',sign=sel_vtx.sign,weight=wgt)
    h.fill('sel_vtx_pt',pt=sel_vtx.pt,weight=wgt)
    h.fill('sel_vtx_eta',eta=sel_vtx.eta,weight=wgt)
    h.fill('sel_vtx_phi',phi=sel_vtx.phi,weight=wgt)
    h.fill('sel_vtx_corrPt',pt=sel_vtx.refit_pt,weight=wgt)
    h.fill('sel_vtx_corrEta',eta=sel_vtx.refit_eta,weight=wgt)
    h.fill('sel_vtx_corrPhi',phi=sel_vtx.refit_phi,weight=wgt)
    h.fill('sel_vtx_type',vtype=sel_vtx.typ,weight=wgt)
    h.fill("sel_vtx_minEleDrJ",dR=np.minimum(sel_vtx.e1.mindRj,sel_vtx.e2.mindRj),weight=wgt)
    h.fill("sel_vtx_minEleDPhiJ",abs_dphi=np.minimum(sel_vtx.e1.mindPhiJ,sel_vtx.e2.mindPhiJ),weight=wgt)
    h.fill("sel_vtx_mindxy_low",mindxy_low=sel_vtx.min_dxy,weight=wgt)
    h.fill("sel_vtx_corrMindxy_low",mindxy_low=sel_vtx.corrMinDxy,weight=wgt)
    h.fill("sel_vtx_sign_etaProd",sign_etaProd=ak.values_astype(np.sign(sel_vtx.e1.eta*sel_vtx.e2.eta),int),weight=wgt)
    h.fill("sel_vtx_CosThetaColl",cosTheta=sel_vtx.cos_collinear,weight=wgt)
    h.fill("sel_vtx_LxyCosThetaColl",LxyCosTheta=sel_vtx.projectedLxy,weight=wgt)
    h.fill("sel_vtx_LxyCosThetaCollZoom",LxyCosThetaZoom=sel_vtx.projectedLxy,weight=wgt)
    h.fill("sel_vtx_LxyCosThetaCollZoomZoom",LxyCosThetaZoomZoom=sel_vtx.projectedLxy,weight=wgt)
    h.fill("sel_vtx_CorrCosThetaColl",cosTheta=sel_vtx.corr_cos_collinear,weight=wgt)
    h.fill("sel_vtx_CorrLxyCosThetaColl",LxyCosTheta=sel_vtx.corrProjectedLxy,weight=wgt)
    h.fill("sel_vtx_CorrLxyCosThetaCollZoom",LxyCosThetaZoom=sel_vtx.corrProjectedLxy,weight=wgt)
    h.fill("sel_vtx_CorrLxyCosThetaCollZoomZoom",LxyCosThetaZoomZoom=sel_vtx.corrProjectedLxy,weight=wgt)
    h.fill("sel_vtx_eleDphi",abs_dphi=sel_vtx.eleDphi,weight=wgt)
    h.fill("sel_vtx_maxMiniRelIso",iso=np.maximum(sel_vtx.e1.miniRelIso,sel_vtx.e2.miniRelIso),weight=wgt)
    h.fill("sel_vtx_maxMiniRelIsoCorr",iso=np.maximum(sel_vtx.e1.miniRelIsoEleCorr,sel_vtx.e2.miniRelIsoEleCorr),weight=wgt)
    h.fill("sel_vtx_e1e2PassConvVeto",passVeto=ak.values_astype((sel_vtx.e1.conversionVeto) & (sel_vtx.e2.conversionVeto),int),weight=wgt)
    
    h.fill("sel_vtx_vxyRes",vxyRes=sel_vtx.sigmavxy,weight=wgt)
    h.fill("sel_vtx_vxySignif",vxySignif=sel_vtx.vxy/sel_vtx.sigmavxy,weight=wgt)

    #
    h.fill("PFMET",met=events.PFMET.pt,weight=wgt)
    h.fill("jetMETdPhi",abs_dphi=np.abs(events.PFJet.METdPhi[:,0]),weight=wgt)
    h.fill("minJetMETdPhi",abs_dphi=ak.min(np.abs(events.PFJet.METdPhi),axis=1),weight=wgt)
    h.fill("nJets",nJets=ak.count(events.PFJet.pt,axis=1),weight=wgt)
    h.fill("lead_jet_pt",jet_pt=events.PFJet.pt[:,0],weight=wgt)
    h.fill("lead_jet_eta",eta=events.PFJet.eta[:,0],weight=wgt)
    h.fill("jetMETratio",jetMETratio=events.PFJet.pt[:,0]/events.PFMET.pt,weight=wgt)
    h.fill("pfCalo_metRatio",met_ratio=np.abs(events.PFMET.pt-events.CaloMET.pt)/events.CaloMET.pt,weight=wgt)
    
    if info['type'] == 'signal':
        h.fill("selMatch_vs_hasMatch",match=events.sel_vtx.isMatched,match_exist=ak.any(events.good_vtx.isMatched,axis=1))
        