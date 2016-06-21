#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys, os, subprocess, time
from lxml import etree

# Comprobación de parámetros pasados al script
if (len(sys.argv) != 2 and len(sys.argv) != 3) or sys.argv[1] not in ["-create", "-start", "-stop", "-destroy", "-monitor"]:
	print chr(27) + "[0;44m" + "Uso del script: python pfinalp1.py [comando] [opciones]" + chr(27) + "[0m"
	print "Lista de comandos:"
	print "	-create		--> Crea el escenario"
	print "	-start n	--> Arranca n servidores (n entre 1 y 5)"
	print "	-stop		--> Detiene los servidores"
	print "	-destroy	--> Detiene los servidores y destruye el escenario"
	print "	-monitor [n]	--> Muestra información sobre los servidores o sobre el servidor n (n entre 1 y 5)"
	sys.exit()
elif len(sys.argv) == 3:
	if sys.argv[1] != '-start' and sys.argv[1] != '-monitor':
		print chr(27) + "[0;41m" + "El comando que ha introducido no utiliza opciones" + chr(27) + "[0m"
		sys.exit()
	
# Parámetro que define la operación a realizar
orden = sys.argv[1]

# Máquinas virtuales
mv = ["c1", "lb", "s1", "s2", "s3", "s4", "s5"]
# Numero máximo de servidores que se pueden arrancar
nserver_max = len(mv) - 2

if orden == '-create':
	print chr(27) + "[0;44m" + "Creando el escenario..." + chr(27) + "[0m"

	# Creamos los ficheros .qcow2 de diferencias
	for i in range (0, len(mv)):
		os.system("qemu-img create -f qcow2 -b cdps-vm-base-p3.qcow2 " + mv[i] + ".qcow2")

	# Leemos la plantilla XML y preparamos para crear los ficheros de especificación XML
	tree = etree.parse('plantilla-vm-p3.xml')
	root = tree.getroot()
	name = root.find("name")
	disksource = root.find("./devices/disk/source")
	interfacesource = root.find("./devices/interface/source")
	
	abspath = os.path.abspath("")
	# Creamos los ficheros de especificación XML de los servers
	interfacesource.set("bridge", "LAN2")
	for i in range (2, len(mv)):
		name.text = mv[i]
		disksource.set("file", os.path.abspath("") + "/" + mv[i] + ".qcow2")
		tree.write(mv[i] + '.xml', xml_declaration = True)
	
	# Creamos los ficheros de especificación XML del cliente c1 y del balanceador lb
	interfacesource.set("bridge", "LAN1")

	name.text = 'c1'
	disksource.set("file", os.path.abspath("") + "/c1.qcow2")
	tree.write('c1.xml', xml_declaration = True)

	name.text = 'lb'
	disksource.set("file", os.path.abspath("") + "/lb.qcow2")
	interfaceb = etree.Element('interface', type = 'bridge')
	devices = root.find("./devices")
	devices.insert(3, interfaceb)
	interfacemodel = etree.Element('model', type = 'virtio')
	interfaceb.insert(0, interfacemodel)
	interfacesourceb = etree.Element('source', bridge = 'LAN2')
	interfaceb.insert(0, interfacesourceb)
	tree.write('lb.xml', xml_declaration = True)

	# Creamos los bridges que soportan las LAN del escenario
	os.system("sudo brctl addbr LAN1")
	os.system("sudo brctl addbr LAN2")
	os.system("sudo ifconfig LAN1 up")
	os.system("sudo ifconfig LAN2 up")

	print chr(27) + "[0;42m" + "Se ha creado el escenario" + chr(27) + "[0m"

elif orden == '-start':
	# Si existe c1.xml es porque se ha creado el escenario
	if os.path.isfile("c1.xml"):
		# Si se pasa un parámetro aparte del comandp (el comando start precisa un parámetro que indique el número de servidores a arrancar)
		if len(sys.argv) == 3 and sys.argv[2].isdigit():
			nserver = int(sys.argv[2])
			# Guardamos dicho parámetro en un fichero de configuración que leerá el script en las órdenes stop y destroy
			server_config = open('.server_config.txt', 'w+')
			server_config.write('%d' % nserver)
			server_config.close()
			# Si el número de servidores a arrancar está entre 1 y 5
			if nserver > 0 and nserver <= nserver_max:
				print chr(27) + "[0;44m" + "Arrancando el escenario..." + chr(27) + "[0m"
				# Para c1, lb y cada uno de los servidores elegidos
				for i in range (0, nserver + 2):
					# Arrancamos su MV y mostramos su consola
					if subprocess.call(['sudo', 'virsh', 'create', mv[i] + '.xml']) != 0:
						os.system("sudo virsh create " + mv[i] + ".xml")
					os.system("sudo virt-viewer " + mv[i] + "&")
				time.sleep(0.25)
				print chr(27) + "[0;42m" + "Se ha arrancado el escenario con %d servidores" % nserver + chr(27) + "[0m"
			else:
				print chr(27) + "[0;41m" + "El número de servidores a arrancar debe estar entre 1 y %d" % nserver_max + chr(27) + "[0m"
		else:
			print chr(27) + "[0;41m" + "Debe indicar el número de servidores a arrancar con un número entre 1 y %d" % nserver_max + chr(27) + "[0m"
	else:
		print chr(27) + "[0;41m" + "Para poder arrancar servidores primero debe crear el escenario" + chr(27) + "[0m"

elif orden == '-stop':
	# Si existe .server_config.txt es que se han arrancado previamente MVs
	if os.path.isfile(".server_config.txt"):
		# Leemos el fichero de configuración que contiene el número de servidores que se han arrancado
		server_config = open('.server_config.txt', 'r')
		nserver_ = server_config.read()
		nserver = int(nserver_)
		print chr(27) + "[0;44m" + "Deteniendo el escenario..." + chr(27) + "[0m"
		# Paramos las MV que se habían arrancado previamente
		for i in range (0, nserver + 2):
			os.system("sudo virsh shutdown " + mv[i])	
		time.sleep(0.25)
		print chr(27) + "[0;42m" + "Se han detenido las MV del escenario" + chr(27) + "[0m"
	else:
		print chr(27) + "[0;41m" + "No se pueden detener MVs ya que ninguna ha sido arrancada" + chr(27) + "[0m"

elif orden == '-destroy':
	# Si existe .server_config.txt es que se han arrancado previamente MVs
	if os.path.isfile(".server_config.txt"):
		# Leemos el fichero de configuración que contiene el número de servidores que se han arrancado
		server_config = open('.server_config.txt', 'r')
		nserver_ = server_config.read()
		nserver = int(nserver_)
		print chr(27) + "[0;44m" + "Destruyendo y liberando el escenario..." + chr(27) + "[0m"
		# Destroy de las MV arrancadas
		for i in range (0, nserver + 2):
			os.system("sudo virsh destroy " + mv[i])
		# Se borra el fichero de configuración antes creado
		os.remove(".server_config.txt")

	# Si existe c1.xml es porque se ha creado el escenario
	if os.path.isfile("c1.xml"):
		# Liberamos el escenario, borrando todos los ficheros creados
		for i in range (0, len(mv)):
			os.remove(mv[i] + ".xml")
			os.remove(mv[i] + ".qcow2")
		# Eliminamos los bridges que soportan las LAN del escenario
		os.system("sudo ifconfig LAN1 down")
		os.system("sudo ifconfig LAN2 down")	
		os.system("sudo brctl delbr LAN1")
		os.system("sudo brctl delbr LAN2")
		print chr(27) + "[0;42m" + "Se ha destruido y liberado el escenario" + chr(27) + "[0m"
	else:
		print chr(27) + "[0;41m" + "El escenario no ha sido creado" + chr(27) + "[0m"

elif orden == '-monitor':
	if len(sys.argv) == 2:
		print chr(27) + "[0;44m" + "Estado de las MVs arrancadas" + chr(27) + "[0m"
		print "Para información sobre una MV en concreto, introduzca su nombre tras el comando monitor"
		print ""
		# Listamos las MV que se encuentran funcionando
		os.system("sudo virsh list --all")
	else:
		# Si existe .server_config.txt es que se han arrancado previamente MVs
		if os.path.isfile(".server_config.txt"):
			# Leemos el fichero de configuración que contiene el número de servidores que se han arrancado
			server_config = open('.server_config.txt', 'r')
			nserver_ = server_config.read()
			nserver = int(nserver_)
			mvname = ''
			for i in range (0, nserver + 2):
				if sys.argv[2] == mv[i]:
					mvname = sys.argv[2]
			if mvname == '':
				print chr(27) + "[0;41m" +  "Introduzca el nombre de una MV que haya sido arrancada" + chr(27) + "[0m"
				sys.exit()			
			else:
				print chr(27) + "[0;44m" + "Información de %s:" % mvname + chr(27) + "[0m"
				os.system("sudo virsh dominfo %s" % mvname)			
				print chr(27) + "[0;44m" + "Estado de %s:" % mvname + chr(27) + "[0m"
				os.system("sudo virsh domstate %s" % mvname)
				print chr(27) + "[0;44m" + "CPU stats de %s:" % mvname + chr(27) + "[0m"
				os.system("sudo virsh cpu-stats %s" % mvname)
