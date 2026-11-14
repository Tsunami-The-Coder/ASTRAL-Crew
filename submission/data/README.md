# NASA OSDR OSD-575 CMP data

- **Study:** NASA Open Science Data Repository OSD-575, SpaceX Inspiration4 Blood Serum Metabolic Panel and Immune/Cardiac Cytokine Arrays.
- **Source file:** `OSD-575_CMP_TRANSFORMED.csv`, downloaded from NASA OSDR's transformed CMP file.
- **Source page:** https://osdr.nasa.gov/bio/repo/data/studies/OSD-575
- **DOI:** https://doi.org/10.26030/mc5d-p710
- **License:** CC0-1.0 as listed on the OSDR study page.
- **SHA-256:** `5eb1e7f025dd8443a9e70111e62bc32afae3432753024489c5c013e401d709d9`
- **Shape:** 28 sample rows × 58 columns.

The browser chart selects serum glucose, creatinine, sodium, potassium, and calcium. It parses the sample name into crew code and collection timepoint, then plots original values with the reference interval included in the source file. It does not average, normalize, impute, or classify samples. The reference interval is only source context and is not an astronaut-specific operational threshold.

The seven samples per crew are from L−92, L−44, L−3, R+1, R+45, R+82, and R+194. The series contains pre-flight and post-flight measurements around the Inspiration4 three-day mission, not continuous in-flight monitoring. These public sample-level values are not used in the synthetic daily check-in baseline or to validate the trend rule.
