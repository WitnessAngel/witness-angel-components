find src/waguilib/ -type f \( -name '*.py' -or -name '*.kv' \)  -print > _list
xgettext --from-code=UTF-8 --files-from=_list -Lpython -o src/waguilib/locale/_messages.pot

msgmerge --update --backup=off src/waguilib/locale/fr/LC_MESSAGES/witnessangel.po src/waguilib/locale/_messages.pot
#USELESS msgmerge --update --backup=off src/waguilib/locale/en/LC_MESSAGES/witnessangel.po src/waguilib/locale/_messages.pot

msgfmt -c -o src/waguilib/locale/fr/LC_MESSAGES/witnessangel.mo src/waguilib/locale/fr/LC_MESSAGES/witnessangel.po
#USELESS msgfmt -c -o src/waguilib/locale/en/LC_MESSAGES/witnessangel.mo src/waguilib/locale/en/LC_MESSAGES/witnessangel.po

