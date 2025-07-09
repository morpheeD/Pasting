for i in a["resources"]:
   if "module" in i  and "vsphere_virtual_machine" in i.values():
     pprint(i["instances"][0]["attributes"]["memory"])
