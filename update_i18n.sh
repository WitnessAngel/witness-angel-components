find src/waguilib/ -type f \( -name '*.py' -or -name '*.kv' \)  -print > __translatable_files
xgettext --from-code=UTF-8 --files-from=__translatable_files -Lpython -o src/waguilib/locale/_messages.pot
msgmerge --update --backup=off src/waguilib/locale/fr/LC_MESSAGES/witnessangel.po src/waguilib/locale/_messages.pot
msgfmt -c -o src/waguilib/locale/fr/LC_MESSAGES/witnessangel.mo src/waguilib/locale/fr/LC_MESSAGES/witnessangel.po


