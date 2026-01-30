[![DOI](https://zenodo.org/badge/265254045.svg)](https://zenodo.org/doi/10.5281/zenodo.10442485)

# Spangler-etal_2026_SustainableCitiesAndSociety

**Collaborative Development of a Pluvial Flood Model and Adaptation Strategies to Advance Resilience in Baltimore**

Ava Spangler<sup>1,2\*</sup>, Antonia Hadjimichael<sup>1,2</sup>, Carlin Blash<sup>1</sup>, Mahsa Adib<sup>3,4</sup>,, Hong Wu<sup>3</sup>, Mark Cameron<sup>5</sup>, Claire Welty<sup>6,7</sup>, Doris Minor-Terrell<sup>8</sup>,, Benjamin Zaitchik<sup>9</sup>

<sup>1 </sup>The Pennsylvania State University Earth and Environmental Systems Institute, University Park, PA, USA

<sup>2 </sup> The Pennsylvania State University Earth and Environmental Systems Institute, University Park PA, USA

<sup>3 </sup> The Pennsylvania State University Department of Landscape Architecture, University Park, PA, USA

<sup>4 </sup> Michigan State University School of Planning, Design and Construction, East Lansing, MI, USA

<sup>5 </sup> Baltimore City Department of Public Works, Baltimore, MD, USA
<sup>6 </sup> University of Maryland Baltimore County Department of Chemical, Biochemical and Environmental Engineering, Baltimore, MD, USA

<sup>7 </sup> University of Maryland Baltimore County Center for Urban Environmental Research and Education, Baltimore, MD, USA

<sup>8 </sup> Broadway East Community & Community Development Corporation, Baltimore, MD, USA

<sup>9 </sup>Johns Hopkins University Department of Earth and Planetary Sciences, Baltimore, MD, USA

\* corresponding author:  aas6791@psu.edu

## Abstract
The intensification of the hydrologic cycle due to climate change poses a
threat to urban areas with aging and under-sized water infrastructure sys-
tems which cannot adequately manage intense storm events. In the City of
Baltimore, Maryland, stormwater infrastructure is challenged by stormwater
(pluvial) flooding, which has damaged housing and disrupted transportation
networks. In this study, a combination of community engagement and hydro-
logic modeling is applied to develop and assess prospective urban flooding
adaptations. Community engagement drives the development of an urban
flooding model (EPA Storm Water Management Model) for the Baltimore
Harbor watershed, integrating complex surface and subsurface stormwater in-
frastructure data and community insights. Adaptations of interest to stake-
holders, including green and gray infrastructure strategies, are simulated.
Enhanced infrastructure maintenance is the most effective adaptation for
reducing flood depths, but has varied effects across the watershed. Spatially-
concentrated greening provides limited benefit to the watershed as a whole,
but moderate benefit in community priority areas. Together, these adap-
tations have the potential to reduce flood depths by as much as 58% in
select locations, which would greatly reducing property damage and trans-
portation impacts, which are primary concerns of stakeholders. This work
builds on the growing body of collaborative modeling literature and shows
that community-engaged research can increase the relevance and credibility
of model representations, resulting in more relevant and usable insights for
communities working to enhance climate resiliency.

## Journal reference
Spangler, A., Hadjimichael, A., Blash, C., Adib, M., Wu, H., Cameron, M., Welty, C., Minor-Terrell, D., Zaitchik, B., Collaborative Development of a Pluvial Flood Model and Adaptation Strategies to Advance Resilience in Baltimore. (Sumbitted to Sustainable Cities and Society Febrary 2026)

## Code reference

## Data reference

### Input data

Spangler, A. (2026). Baltimore SWMM input file [Data set]. Zenodo. https://doi.org/some-doi-number

## Contributing Modeling Software  
| Software      | Version       | Repository    | DOI           |
| ------------- | ------------- | ------------- | ------------- |
| EPA SWMM      | 5.2.4         | [EPA SWMM Repository](https://github.com/USEPA/Stormwater-Management-Model.git)  | -  | 
| PCSWMM        | 7.7           | [PCSWMM Free Educational Lisence](https://www.pcswmm.com/Grant)  | -  |
| PySWMM        | 2.1.0         | [Pyswmm Repository](https://github.com/pyswmm/pyswmm.git)  | [https://doi.org/10.21105/joss.02292](https://doi.org/10.21105/joss.02292)  |
| ------------- | ------------- | ------------- | ------------- |


## Reproduce my experiment
Fill in detailed info here or link to other documentation to thoroughly walkthrough how to use the contents of this repository to reproduce your experiment. Below is an example.


1. Install the software components required to conduct the experiment from [contributing modeling software](#contributing-modeling-software)
2. Install all package dependencies listed in environment.yml using conda env create --file environment.yml
3. Activate environment using conda activate Spangler-etal_2026_SustainableCitiesAndSociety
4. Download and install the supporting [input data](#input-data) required to conduct the experiment
5. Run the following scripts in the `workflow` directory to re-create this experiment:

| Script Name | Description | How to Run |
| --- | --- | --- |
| `BSEC_SWMM_model.py` | Script to run the first part of my experiment | `python3 BSEC_SWMM_model.py -f /path/to/inputdata/BSEC_SWMM_model.inp` |

## Reproduce my figures
Use the scripts found in the `figures` directory to reproduce the figures used in this publication.

| Figure Number(s) | Script Name | Description | How to Run |
| --- | --- | --- | --- |
| 1-6 | `BSEC_SWMM_Plotter.py` | Plots all figures in the journal aricle | `python3 BSEC_SWMM_Plotter.py -input /path/to/inputs -output /path/to/outuptdir` |
