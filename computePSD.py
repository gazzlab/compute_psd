"""
==================
   compute_psd
==================

Epochs resting MEG data into 4 second intervals, removes EOG artifacts, computes noise covariance, inverse operator and PSD.

"""
# Authors: Vincent Rupp Jr. <<vrupp@rohan.sdsu.edu>>; Morgan Hough <<morgan@gazzaleylab.ucsf.edu>>

print __doc__

import numpy as np
import pylab as pl
import mne
from mne import fiff, write_cov
from mne.fiff import Raw, pick_types
from mne.minimum_norm import read_inverse_operator, compute_source_psd_epochs, apply_inverse_epochs, write_inverse_operator, make_inverse_operator

###############################################################################
# Set parameters
# (Better, more flexible parameter setting to be added here)
data_path = '/home/vrupp/data/restMEG/' 
subj = raw_input('Subject ID:')
fname_raw = data_path + subj + '/' + subj + '_rest_raw_sss.fif'  
fname_fwd = data_path + subj + '/' + subj + '_rest_raw_sss-oct-6-fwd.fif'
label_name = 'lh.BA45' # how can we do both hemi simultaneously? 
fname_label = '/home/vrupp/data/freesurfer/subjects/' + subj + '/' + 'label/%s.label' % label_name 

event_id, tmin, tmax = 1, 0.0, 4.0
snr = 1.0 
lambda2 = 1.0 / snr ** 2
method = "dSPM" 

# Load data
label = mne.read_label(fname_label)
raw = fiff.Raw(fname_raw)
forward_meg = mne.read_forward_solution(fname_fwd)

# Estimate noise covariance from teh raw data
cov = mne.compute_raw_data_covariance(raw, reject=dict(eog=150e-6))
write_cov(data_path + subj + '/' + subj + '-cov.fif', cov)

# Make inverse operator
info = raw.info
inverse_operator = make_inverse_operator(info, forward_meg, cov, loose=None, depth=0.8)

# Epoch data into 4s intervals
events = mne.make_fixed_length_events(raw, 1, start=0, stop=None, 
		duration=4.)

# Set up pick list: (MEG minus bad channels)
include = []
exclude = raw.info['bads']
picks = fiff.pick_types(raw.info, meg=True, eeg=False, stim=False, eog=True, 
		include=include, exclude=exclude)

# Read epochs and remove bad epochs
epochs = mne.Epochs(raw, events, event_id, tmin, tmax, proj=True, 
		picks=picks, baseline=(None, 0), preload=True, 
		reject=dict(grad=4000e-13, mag=4e-12, eog=150e-6))

# Compute the inverse solution
stc = apply_inverse_epochs(epochs, inverse_operator, lambda2, method)
#stc.save(data_path + subj + '/' + subj + '_rest_raw_sss-oct-6-inv.fif')

# define frequencies of interest
fmin, fmax = 0., 70.
bandwidth = 4.  # bandwidth of the windows in Hz

# compute source space psd in label

# Note: By using "return_generator=True" stcs will be a generator object
# instead of a list. This allows us so to iterate without having to
# keep everything in memory.

stcs = compute_source_psd_epochs(epochs, inverse_operator, lambda2=lambda2,
                                 method=method, fmin=fmin, fmax=fmax,
                                 bandwidth=bandwidth, label=label, return_generator=True)
#stcs.save('/usr/local/freesurfer/subjects/' + subj + '/meg/dspm_snr-1_PSD_stc')

# compute average PSD over the first 10 epochs
n_epochs = 10
for i, stc in enumerate(stcs):
    if i >= n_epochs:
        break

    if i == 0:
        psd_avg = np.mean(stc.data, axis=0)
    else:
        psd_avg += np.mean(stc.data, axis=0)

psd_avg /= n_epochs
freqs = stc.times  # the frequencies are stored here

pl.figure()
pl.plot(freqs, psd_avg)
pl.xlabel('Freq (Hz)')
pl.ylabel('Power Spectral Density')
pl.show()

