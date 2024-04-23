import sys
import pandas as pd
import plotTools as ptools
import json
from pathlib import Path

# Signal
def get_dict_fromCutflow(cf):
    sig_samples = cf.keys()
    dict = {s:ptools.signalPoint(s) for s in sig_samples}
    dict = pd.DataFrame.from_dict(dict, orient='index')
    return dict

def get_signal_point_dict(sig_histo):
    '''
    Get dictionary of signal sub-process, i.e. mass point, lifetime etc.

    sig_histo takes util.load(coffea_file)[0]
    '''

    return get_dict_fromCutflow(sig_histo['cutflow'])

def get_signal_cutflow_dict(sig_histo, branch):
    '''
    Get dictionary of cutflow for signal
    
    Some available branches are:
    - cutflow: efficiency
    - cutflow_cts: xsec-weighted event count
    - cutflow_vtx_matched: fraction that selected vtx is truth-matched
    - cutflow_nevts: raw count
    '''

    df = pd.DataFrame.from_dict(sig_histo[branch], orient='index')

    cutnames = get_signal_list_of_cuts(sig_histo)
    df.columns = cutnames
    
    return df

def get_signal_list_of_histograms(sig_histo):
    '''
    Get list of histograms
    '''
    return list(sig_histo.keys())

def get_signal_list_of_cuts(sig_histo, get_cut_idx = False):
    '''
    Get dictionary of cuts
    '''

    sig_sample = list(sig_histo['cutflow'].keys())[0]

    cut_dict = {cname:ptools.getCut(sig_histo['cutDesc'][cname]) for cname in sig_histo['cutDesc'].keys()}

    cut_idx = list(cut_dict.keys())
    cut_name = list(cut_dict.values())
    print(json.dumps(cut_dict,indent=4))

    cut_name = list(map(lambda x: x.replace('No cuts', 'Preselections'), cut_name))
    cut_name = list(map(lambda x: x.replace('Baseline Selection', '0 < n(jet) < 3 & n(good vertex) > 0'), cut_name))

    if get_cut_idx:
        cut = cut_idx
    else:
        cut = cut_name
    
    return cut


# Background
def get_bkg_point_dict(bkg_histos, selected_process = 'all'):
    '''
    Get dictionary of background sub-process

    bkg_histos takes a dictionary whose items are util.load(coffea_file)[0]
    '''
    
    sample_dict = {}
    for process in bkg_histos.keys():
        subprocesses = list(bkg_histos[process]['cutflow'].keys())
    
        for sub in subprocesses:
            sample_dict[sub] = process
    
    sample_df = pd.DataFrame.from_dict(sample_dict, orient='index', columns=['Process'])

    if selected_process != 'all':
        sample_df = sample_df.loc[sample_df['Process'] == selected_process]

    return sample_df

def get_bkg_cutflow_df(bkg_histos, branch, process = 'all'):
    '''
    Get dictionary of cutflow for background
    
    Some available branches are:
    - cutflow: efficiency
    - cutflow_cts: xsec-weighted event count
    - cutflow_nevts: raw count
    '''

    cut_idx = get_bkg_list_of_cuts(bkg_histos, get_cut_idx = True)
    cut_name = get_bkg_list_of_cuts(bkg_histos, get_cut_idx = False)

    if process != 'all':
        cutflow = bkg_histos[process][branch]
        cutflow = pd.DataFrame.from_dict(cutflow, orient='index')
    
        if branch != 'cutflow':
            cutflow.loc["Total"] = cutflow.sum()
            
        else:            
            total_cts_nocut = 0
            total_cts_after_cut = {cut: 0 for cut in cut_idx}
            
            for subprocess in list(bkg_histos[process]['cutflow'].keys()):
                total_cts_nocut += bkg_histos[process]['cutflow_cts'][subprocess]['all'] / bkg_histos[process]['cutflow'][subprocess]['all']
            
                for cut in cut_idx:
                    total_cts_after_cut[cut] += bkg_histos[process]['cutflow_cts'][subprocess][cut]
    
            total_eff_after_cut = {cut: total_cts_after_cut[cut] / total_cts_nocut for cut in cut_idx}
    
            cutflow.loc["Total"] = total_eff_after_cut

    else:
        # for each process
        total_cts_nocut = {}
        total_cts_after_cut = {}
        total_eff_after_cut = {}

        total_raw_cts_after_cut = {}

        for process in bkg_histos.keys():
            total_cts_nocut[process] = 0
            total_cts_after_cut[process] = {cut: 0 for cut in cut_idx}
            total_raw_cts_after_cut[process] = {cut: 0 for cut in cut_idx}
            
            for subprocess in list(bkg_histos[process]['cutflow'].keys()):
                total_cts_nocut[process] += bkg_histos[process]['cutflow_cts'][subprocess]['all'] / bkg_histos[process]['cutflow'][subprocess]['all']
                for cut in cut_idx:
                    total_cts_after_cut[process][cut] += bkg_histos[process]['cutflow_cts'][subprocess][cut]
                    total_raw_cts_after_cut[process][cut] += bkg_histos[process]['cutflow_nevts'][subprocess][cut]
            
            total_eff_after_cut[process] = {cut: total_cts_after_cut[process][cut] / total_cts_nocut[process] for cut in cut_idx}

        total_cts_all_process_after_cut = {cut: 0 for cut in cut_idx}
        total_cts_all_process_no_cut = 0
        total_eff_after_cut['Total'] = {}
        
        for cut in cut_idx:
            for process in bkg_histos.keys():
                # for all bkg process summed
                total_cts_all_process_after_cut[cut] += total_cts_after_cut[process][cut]
                total_cts_all_process_no_cut += total_cts_nocut[process]
        
            total_eff_after_cut['Total'][cut] = total_cts_all_process_after_cut[cut] / total_cts_all_process_no_cut
        
        if branch == 'cutflow':
            cutflow = pd.DataFrame.from_dict(total_eff_after_cut, orient='index')
        elif branch == 'cutflow_cts':
            cutflow = pd.DataFrame.from_dict(total_cts_after_cut, orient='index')
            cutflow.loc['Total'] = cutflow.sum()
        elif branch == 'cutflow_nevts':
            cutflow = pd.DataFrame.from_dict(total_raw_cts_after_cut, orient='index')
            cutflow.loc['Total'] = cutflow.sum()
    
    cutflow.columns = cut_name
    
    return cutflow

def get_bkg_list_of_cuts(bkg_histos, get_cut_idx = False):
    '''
    Get dictionary of cuts
    '''

    process = list(bkg_histos.keys())[-1]
    subprocess = list(bkg_histos[process]['cutflow'].keys())[-1]

    cut_dict = {cname:ptools.getCut(bkg_histos[process]['cutDesc'][cname]) for cname in bkg_histos[process]['cutDesc'].keys()}

    cut_idx = list(cut_dict.keys())
    cut_name = list(cut_dict.values())

    cut_name = list(map(lambda x: x.replace('No cuts', 'Preselections'), cut_name))
    cut_name = list(map(lambda x: x.replace('Baseline Selection', '0 < n(jet) < 3 & n(good vertex) > 0'), cut_name))

    if get_cut_idx:
        cut = cut_idx
    else:
        cut = cut_name
    
    return cut

def bkg_categories(cutflow):
    allNames = list(cutflow.keys())
    bkgCats = list(set([n.split("_")[2] for n in allNames]))
    output_samples = {b:[] for b in bkgCats}
    output_names = {b:[] for b in bkgCats}
    for name in allNames:
        parts = name.split("_")
        bgkCat = parts[2]
        subSample = "_".join(parts[3:])
        output_samples[bgkCat].append(name)
        output_names[bgkCat].append(subSample)
    return output_samples, output_names


def add_signal_info_to_df(df):
    m1_list = []
    delta_list = []
    ctau_list = []
    
    for point in df.index.values:
        sig_dict = ptools.signalPoint(point)
        m1_list.append(sig_dict['m1'])
        delta_list.append(sig_dict['delta'])
        ctau_list.append(sig_dict['ctau'])
    
    df['m1'] = m1_list
    df['delta'] = delta_list
    df['ctau'] = ctau_list
    
    df = df.sort_values(by=['m1']) # sort by m1

    return df

def save_df_to_csv(df, outdir, outname, isSignal = False):
    Path(outdir).mkdir(parents=True, exist_ok=True)

    if isSignal:
        df = add_signal_info_to_df(df)
    
    df.to_csv(f'{outdir}/{outname}.csv')

    print(f'Saved: {outdir}/{outname}.csv')


