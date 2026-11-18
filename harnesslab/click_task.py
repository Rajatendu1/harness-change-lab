"""Fixed public Click pilot input identities, prepare-only. No run authority.

Only the public base source file hashes are present. Neither fixed source nor
protected regression content is installed in the editing helper.
"""
import hashlib
from .source_bundle import validate_sources

TASK_ID = 'm1-click-hyphenated-help-wrap'
BASE_COMMIT = '8abb77a8432e03ed14a95f972b44f905279415a7'
MODEL = 'openai/gpt-oss-120b'
EDITABLE = ('src/click/formatting.py',)
ISSUE = ('Prevent Click help text wrapping from splitting hyphenated words or '
         'long words such as option names. Edit src/click/formatting.py only.')
BASE_HASHES = {'LICENSE.txt': '9a8ad106a394e853bfe21f42f4e72d592819a22805d991b5f3275029292b658d', 'src/click/__init__.py': '5abfc54d37d47cc788b7e7a05e9514787f8c5a0b7db429d0f24d748ac89964ca', 'src/click/_compat.py': '8db1da2965cf3e5dc66c6c53833cbc613ea1cd2440b9d0eb6aa8360eb46d4913', 'src/click/_termui_impl.py': '51b485ef15b4858817817296ea16a85a8fead9ab097fe4fda7778897b8cc82f9', 'src/click/_textwrap.py': 'ed9d0ded59a7fbae933524d4c29e8e5c96dc5174666044fd87d736b9c0fca104', 'src/click/_utils.py': 'c7a62c70514253d091cbca49917fe16281556db1aa83bb389532180c47dc1233', 'src/click/_winconsole.py': 'a6f0d49ef0be806a9730bd64a2e5b373a95d49de91fd7728595ff31d773f2db7', 'src/click/core.py': '2f875ed5e331828e48df459732de8551376cd48e706164b285d3afe9e5626287', 'src/click/decorators.py': 'b8d08ddd7930a3df66003864bb2826e6dd11f14fe46411618d5e566f81d6efc1', 'src/click/exceptions.py': '1ef498df81b86ae8ff6d8451f3e4fc094f09c2aff5f8e72c454e1ecdfa337849', 'src/click/formatting.py': 'f125b628692f8dfcfd43535b7a88cc1ee64137471f9d0243b389aa0cfea85e6b', 'src/click/globals.py': '80cf8d87a0383341c1fd2824685e4ce2770618c0c773f7e51d7bbdfe88781845', 'src/click/parser.py': 'a09f9f53fde6bf1ba022e36d1da0804d9e7a9601261d18208c9892a84818ae30', 'src/click/py.typed': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'src/click/shell_completion.py': 'c5fcba42d9c50bf90367b21a7a80c32fb43f6dda55d0847c7e357b4c95f4e71a', 'src/click/termui.py': '16f6546b36d647d191788fc912e32d93e8b64289517f004e6d9604f4896ad1ca', 'src/click/testing.py': 'e95823823bf2aa65739c2b064778c2893608eaec46080fcd7b7787adf9489b37', 'src/click/types.py': '30a39185da37bbd98ef47153f7bfd310b04eac44bd9b9b2fe15998406337757e', 'src/click/utils.py': '4720e22c292047ff1a747546b1ba80e96d1d8e8158e2e21ff01cdddb6498db17'}
BASE_NAMES = tuple(sorted(BASE_HASHES))


def validate_base(sources):
    validate_sources(sources)
    if set(sources) != set(BASE_HASHES):
        raise ValueError('Exact pinned Click base files required')
    if any(hashlib.sha256(data).hexdigest() != BASE_HASHES[name]
           for name,data in sources.items()):
        raise ValueError('Pinned Click base identity mismatch')
    return True
