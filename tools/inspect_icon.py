import pefile
pe_path = 'dist\\intellipal.exe'
try:
    pe = pefile.PE(pe_path)
except Exception as e:
    print('PE load error:', e)
    raise SystemExit(1)
rt_icon = 3
rt_group_icon = 14
icons = 0
groups = 0
if hasattr(pe, 'DIRECTORY_ENTRY_RESOURCE'):
    for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        try:
            idget = entry.id
        except Exception:
            idget = getattr(entry.struct, 'Id', None)
        if idget == rt_icon:
            icons += 1
        if idget == rt_group_icon:
            groups += 1
print('RT_ICON count:', icons)
print('RT_GROUP_ICON count:', groups)
