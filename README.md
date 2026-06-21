[![DOI](https://zenodo.org/badge/265254045.svg)](https://zenodo.org/doi/10.5281/zenodo.10442485)

# Spangler-etal_2026_SustainableCitiesAndSociety

**Co-Designing Stormwater Adaptations Through Community-Informed Urban Pluvial Flood Modeling**

Ava Spangler<sup>1,2\*</sup>, Antonia Hadjimichael<sup>1,2</sup>, Carlin Blash<sup>1</sup>, Mahsa Adib<sup>3,4</sup>, Hong Wu<sup>3</sup>, Mark Cameron<sup>5</sup>, Claire Welty<sup>6,7</sup>, Doris Minor-Terrell<sup>8</sup>, Benjamin Zaitchik<sup>9</sup>.

- <sup>1 </sup>The Pennsylvania State University; Earth and Environmental Systems Institute, University Park, PA, USA.
- <sup>2 </sup> The Pennsylvania State University; Earth and Environmental Systems Institute, University Park PA, USA.
- <sup>3 </sup> The Pennsylvania State University; Department of Landscape Architecture, University Park, PA, USA.
- <sup>4 </sup> Michigan State University; School of Planning, Design and Construction, East Lansing, MI, USA.
- <sup>5 </sup> Baltimore City Department of Public Works; Baltimore, MD, USA.
- <sup>6 </sup> University of Maryland Baltimore County; Department of Chemical, Biochemical and Environmental Engineering, Baltimore, MD, USA.
- <sup>7 </sup> University of Maryland Baltimore County; Center for Urban Environmental Research and Education, Baltimore, MD, USA.
- <sup>8 </sup> Broadway East Community & Community Development Corporation; Baltimore, MD, USA.
- <sup>9 </sup>Johns Hopkins University; Department of Earth and Planetary Sciences, Baltimore, MD, USA.
- \* corresponding author:  aas6791@psu.edu

## Abstract
The intensification of the hydrologic cycle due to climate change poses a threat to urban areas with aging and under-sized water infrastructure systems which often fail to adequately manage intense storm events. The City of Baltimore, Maryland, experiences recurrent stormwater (pluvial) flooding that overwhelms drainage infrastructure, damages housing and disrupts transportation. Adaptations are urgently needed to manage this threat; however, flood mitigation strategies frequently fail to integrate the lived experiences of residents into infrastructure planning. Engaging communities in pluvial flood modeling is often limited to hazard identification or model validation, while collaborative development of adaptation strategies is uncommon. This study presents a co-designed urban flood modeling framework in which community and technical experts directly inform flood model development and adaptation design through long-term and iterative engagement. The EPA Storm Water Management Model (SWMM) is used to integrate city-provided drainage infrastructure data, community-mapped flood locations, and local expert knowledge of local hydrologic processes. Three adaptations of interest to stakeholders, including green infrastructure, enhanced maintenance, and a combination of both, are simulated and compared across three scaled rainfall scenarios. Enhanced infrastructure maintenance is found to be the most effective adaptation, reducing flood depths at priority intersections, though with spatially variable effects across the watershed. Spatially concentrated greening provides limited benefit to the watershed as a whole. Together, these adaptations have the potential to reduce flood depths by as much as 55% in select locations, which would greatly reduce impacts on local stakeholders. This work demonstrates that co-produced flood models can serve as shared tools for learning and deliberation. Furthermore, these models can test adaptation options that are grounded in both hydrologic process and community priorities, resulting in more relevant and usable insights for communities working to prepare for climate impacts.  

## Journal reference
Spangler, A., Hadjimichael, A., Blash, C., Adib, M., Wu, H., Cameron, M., Welty, C., Minor-Terrell, D., Zaitchik, B., Collaborative Development of a Pluvial Flood Model and Adaptation Strategies to Advance Resilience in Baltimore. (Sumbitted to Sustainable Cities and Society February 2026)

## Code reference

## Data reference

### Input data

- Base model - `inputdata/Inner_Harbor_Model_V24.inp`
- Inlet Cleaning scenario - `inputdata/Inner_Harbor_Model_V24_inlets.inp`
- Vacant Lot Greening scenario - `inputdata/Inner_Harbor_Model_V24_vacants.inp`
- Both Scenari0 - `inputdata/Inner_Harbor_Model_V24_inlets+vacants.inp`
- Please note that associated report (.rpt) and other files are also provided for reference.

## Contributing Modeling Software  
| Software      | Version       | Repository    | DOI           |
| ------------- | ------------- | ------------- | ------------- |
| EPA SWMM      | 5.2.4         | [EPA SWMM Repository](https://github.com/USEPA/Stormwater-Management-Model.git)  | -  | 
| PCSWMM        | 7.7           | [PCSWMM Free Educational Lisence](https://www.pcswmm.com/Grant)  | -  |
| PySWMM        | 2.1.0         | [Pyswmm Repository](https://github.com/pyswmm/pyswmm.git)  | [https://doi.org/10.21105/joss.02292](https://doi.org/10.21105/joss.02292)  |


## Reproduce my experiment
1. Install the software components required to conduct the experiment from [contributing modeling software](#contributing-modeling-software).
2. Install all package dependencies listed in `environment.yml` using `conda env create --file environment.yml`
3. Activate environment using `conda activate BSEC_SWMM`
4. Download the supporting `inputdata` required to conduct the experiment, all SWMM .inp and associated files.
5. Run the `BSEC_SWMM_analysis.py` script in the `scripts` directory to re-create the Baltimore flooding adaptation experiment.
6. Run the `BSEC_SWMM_UQ.py` script in the `scripts` directory to re-create the model uncertainty analysis.
   -> Please note that this code can be executed via command line with `python BSEC_SWMM_uncertainty.py --inp Inner_Harbor_Model_V24.inp --n 500` for convenience on HPC environments.

## Reproduce my figures
1. Run the `BSEC_SWMM_plotter.py` script found in the `scripts` directory to reproduce the figures used in this publication. This script will prepare .csv files for Fig6, which can then be imported to GIS for visualization.
2. Run the `BSEC_SWMM_uncertainty_plotter.py` script found in the `scripts` directory to reproduce the uncertainty quantification experiment figures.