import sys
from textwrap import dedent
import subprocess as sp

import pytest

from helpers import Recipes, ensure_missing, tmp_env_matrix
from bioconda_utils import pkg_test
from bioconda_utils import utils
from bioconda_utils import build

# TODO:
# need tests for channel order and extra channels (see
# https://github.com/bioconda/bioconda-utils/issues/31)
#


SKIP_OSX = sys.platform.startswith('darwin')


RECIPE_ONE = dedent("""
one:
  meta.yaml: |
    package:
      name: one
      version: 0.1
    test:
      commands:
        - "ls -la"
""")


RECIPE_CUSTOM_BASE = dedent("""
one:
  meta.yaml: |
    package:
      name: one
      version: 0.1
    test:
      commands:
        - "ls -la"
        - locale  # not present in default image
    extra:
      container:
        base: "debian:latest"
""")


# Skip mulled_test on default since we already run pkg_test.test_package for every test case.
def _build_pkg(recipe, mulled_test=False):
    r = Recipes(recipe, from_string=True)
    r.write_recipes()
    env_matrix = list(utils.EnvMatrix(tmp_env_matrix()))[0]
    recipe = r.recipe_dirs['one']
    built_package = utils.built_package_path(recipe)
    ensure_missing(built_package)
    build.build(
        recipe=r.recipe_dirs['one'],
        recipe_folder='.',
        env=env_matrix,
        mulled_test=mulled_test,
    )
    return built_package


@pytest.mark.skipif(SKIP_OSX, reason='skipping on osx')
def test_pkg_test():
    """
    Running a mulled-build test shouldn't cause any errors.
    """
    built_package = _build_pkg(RECIPE_ONE)
    res = pkg_test.test_package(built_package)


@pytest.mark.skipif(SKIP_OSX, reason='skipping on osx')
def test_pkg_test_mulled_build_error():
    """
    Make sure calling mulled-build with the wrong arg fails correctly.
    """
    built_package = _build_pkg(RECIPE_ONE)
    with pytest.raises(sp.CalledProcessError):
        res = pkg_test.test_package(built_package, mulled_args='--wrong-arg')


@pytest.mark.skipif(SKIP_OSX, reason='skipping on osx')
def test_pkg_test_custom_base_image():
    """
    Running a mulled-build test with a custom base image.
    """
    build_package = _build_pkg(RECIPE_CUSTOM_BASE)
    res = pkg_test.test_package(build_package, base_image='debian:latest')


@pytest.mark.skipif(SKIP_OSX, reason="skipping on osx")
def test_pkg_test_conda_image():
    """
    Running a mulled-build test with a non-default conda image.
    """
    # Inspects the installing conda version by writing $PREFIX/conda-version as
    # a post-link step -- but only if we are actually doing mulled tests, i.e.,
    # when $PREFIX == /usr/local.
    recipe = dedent("""
        one:
          meta.yaml: |
            package:
              name: one
              version: 0.1
            test:
              commands:
                - '[ "${PREFIX}" != /usr/local ] || cat /usr/local/conda-version'
                - '[ "${PREFIX}" != /usr/local ] || grep -F ''conda 4.3.11'' /usr/local/conda-version'
          post-link.sh: |
            #!/bin/bash
            if [ "${PREFIX}" == /usr/local ] ; then
                /opt/conda/bin/conda --version > /usr/local/conda-version
            fi
    """)
    build_package = _build_pkg(recipe)
    pkg_test.test_package(build_package, conda_image="continuumio/miniconda3:4.3.11")
