pkgdatadir = get_option('prefix') / get_option('datadir') / meson.project_name()
moduledir = pkgdatadir / 'souvenir'
gnome = import('gnome')

blueprints = custom_target('blueprints',
  input: files(
    'blueprint/cell.blp',
    'blueprint/window.blp',
  ),
  output: [
    'cell.ui',
    'window.ui',
  ],
  build_subdir: 'ui',
  command: [find_program('blueprint-compiler'), 'batch-compile', '--minify', '@OUTDIR@', '@CURRENT_SOURCE_DIR@/blueprint', '@INPUT@'],
)

gnome.compile_resources('souvenir',
  'souvenir.gresource.xml',
  gresource_bundle: true,
  dependencies: blueprints,
  install: true,
  install_dir: pkgdatadir,
)

python = import('python')

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').full_path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', get_option('prefix') / get_option('localedir'))
conf.set('pkgdatadir', pkgdatadir)

configure_file(
  input: 'souvenir.in',
  output: 'souvenir',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'rwxr-xr-x'
)

install_subdir(
  'libsouvenir',
  install_dir: pkgdatadir,
)