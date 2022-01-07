find src/wacomponents/ -type f \( -name '*.py' -or -name '*.kv' \)  -print > __translatable_files
xgettext --from-code=UTF-8 --files-from=__translatable_files -Lpython -o src/wacomponents/locale/_messages.pot
msgmerge --update --backup=off src/wacomponents/locale/fr/LC_MESSAGES/witnessangel.po src/wacomponents/locale/_messages.pot
msgfmt -c -o src/wacomponents/locale/fr/LC_MESSAGES/witnessangel.mo src/wacomponents/locale/fr/LC_MESSAGES/witnessangel.po


