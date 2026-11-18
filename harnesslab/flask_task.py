"""Fixed public Flask task identities, preparation only. No run authority.

Narrowed to blueprint-name rejection, not the broader historical task card.
Fixed source and protected test bytes are not part of this base identity map.
"""
import hashlib
from .source_bundle import validate_sources
TASK_ID = 'prepared-flask-blueprint-dotted-name'
BASE_COMMIT = 'd8c37f43724cd9fb0870f77877b7c4c7e38a19e0'
EDITABLE = ('src/flask/blueprints.py',)
ISSUE = 'Reject blueprint names containing a dot with ValueError. Edit src/flask/blueprints.py only.'
BASE_HASHES = {'LICENSE.rst': '489a8e1108509ed98a37bb983e11e0f7e1d31f0bd8f99a79c8448e7ff37d07ea', 'setup.cfg': 'e8d91d82eba2977432cf2cb878f1aae83c771f3f4bd3666622f8b9e1c65f53ed', 'setup.py': 'e45603776a89f88d476689f8635326b9bb15ac159c34d50c4a18bb70236632c0', 'src/flask/__init__.py': 'a9ce94aeef61c020e10ac72846cae4471e7db34eb117ac999353724d41194dd3', 'src/flask/__main__.py': '6d8b7d7846a845059d7a3107143f11131f63c5511d669b44085b15ec5e3d2279', 'src/flask/app.py': 'b68a51cacdca7ce4ae6f9ede160a53bf749abbfe58fde0b39b7e932dad617500', 'src/flask/blueprints.py': '4491da7637d5d262c95fb1992fccf5d8236a9608b8934e6f607821098436569c', 'src/flask/cli.py': '88dd692f649ebc4e4d9af7b2fb45b09f11b79e2a595c8884fff11de25c7722e3', 'src/flask/config.py': '41730e6ad37b8ce3bd659f1217ef3e07a7512c4c27c14891378719d840eca78a', 'src/flask/ctx.py': '86d6af5bf5acb1045ccc5d49353153f118d6321aa747146045a60609b74277c0', 'src/flask/debughelpers.py': 'c24e47b4bc0436c4387bcb64c5f067eb2914795443b8c6d008a82d1157ba8f19', 'src/flask/globals.py': '71677e4768541f756a3e19e640dc30f3ddad412e988ea83fc20f14bd6d4cecd3', 'src/flask/helpers.py': '1200d03393e11f6eb165b7708b822b4e978afce046e5fa2a822891559a9a0593', 'src/flask/json/__init__.py': '77e75bd8324c012ab41bb088f89be86de8511356ac351197d6b203435185f563', 'src/flask/json/tag.py': '7f2b371c12ecb161ee300209b9371fd8ad1b0ada2c78f04a5c85804991048e75', 'src/flask/logging.py': 'd68fe18ab546a9d8fb4817444e7857ec80239251bcf515e5af0cffd828f34101', 'src/flask/py.typed': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'src/flask/scaffold.py': '71cf79a0a66ff57fbce26eae9921a31f8453f8c653b9509e021e4da6b43cbaa0', 'src/flask/sessions.py': '29bef3638a8120e536730d71339990fca9a061404315b5185a3964ab4105622b', 'src/flask/signals.py': '1d05a00445e5acb6c7c0b0685aa012b4929c37eaec075fc030ef3e559ecb0cea', 'src/flask/templating.py': '97de950f7f494349ee7b805c8fbc19e3e1565acfa9a4bc6f8010a9c034382809', 'src/flask/testing.py': '3ac1d3fb607bd1a6d61f7ba563d21b84b7215c87b28f72fe71f7036bcf30bf91', 'src/flask/typing.py': 'eb98baf1e7e801f69c0e173d837faa0cf33225d4e0e1c80856fe1ebdcf02dd5f', 'src/flask/views.py': '1763e958f9687b8c74f74e885239cf72c3aa83962f99021f934eff9457800f8b', 'src/flask/wrappers.py': 'e806c22038deecec61d372d818d6274e52a0cc2deafe55a0d41a541d385c942f'}
BASE_NAMES = tuple(sorted(BASE_HASHES))


def validate_base(sources):
    validate_sources(sources)
    if sources.keys() != BASE_HASHES.keys():
        raise ValueError('Exact pinned Flask base files required')
    if any(hashlib.sha256(data).hexdigest() != BASE_HASHES[name] for name, data in sources.items()):
        raise ValueError('Pinned Flask base identity mismatch')
    return True
