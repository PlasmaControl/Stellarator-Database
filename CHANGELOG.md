# Changelog


## v0.4.0

- **`RBC`, `RBS`, `ZBS` and `ZBC` are no longer written to `configurations.csv`**,
  in both the DESC (`desc_to_csv`) and VMEC (`vmec_to_csv`) paths. These held the
  boundary surface Fourier coefficients as long comma-separated lists of numbers
  in scientific notation, which were unreadable in the database UI and were not
  used by anything.
- **`m` and `n` in `configurations.csv` now hold the resolution of the boundary
  surface** — the maximum poloidal and toroidal mode numbers of its double Fourier
  series — rather than the lists of mode numbers that accompanied the removed
  coefficient arrays. Each is now a single integer instead of a comma-separated
  list.
- The uploaded surface plot is no longer labelled with the configuration name
  (`plot_surfaces` is called without `label`), so it no longer carries a legend.
- **Boundary elongation and curvature extrema in `configurations.csv`:**
  `max_elongation`, `min_elongation`, `max_curvature` and `min_curvature`.
  Extrema are taken over absolute values. Elongation comes from
  `a_major/a_minor` and curvature from `curvature_k2_rho`, the second principal
  curvature of the boundary surface, in inverse meters.

