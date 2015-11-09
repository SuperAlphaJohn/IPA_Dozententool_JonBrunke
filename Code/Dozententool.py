#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
Created on 04.02.2014

@author: brnk
'''

#!/usr/bin/python
 
# Import PySide classes
import sys
from PySide.QtCore import *
from PySide.QtGui import *
from PySide.QtSql import *
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Frame
from reportlab.platypus.flowables import PageBreak
from reportlab.pdfgen import *
import time
import os
import pyodbc
from _elementtree import Element
from datetime import datetime
from reportlab.lib.colors import lightgrey, gray
from cgitb import grey
import pydoc
from pydoc import *

cnxn = pyodbc.connect('DRIVER={SQL Server Native Client 11.0};SERVER=CLT-MOB-T-6251\SQLEXPRESS;DATABASE=db_planungstool;UID=sa;PWD=gfpj8YYA')

newData = []
currentData = []
currentDataIds = []
errorDataIds = []
errorDataNewStunden = []

"""
Klasse Dozentenberichte
Zum Abrufen der PersonenIds.
"""
class Dozentenberichte(QWidget):
    """
    Konstruktor Dozentenberichte.
    """
    def __init__(self, benutzerPersKuerzel, parent=None):
        self.benutzerPersKuerzel = benutzerPersKuerzel
        #self.personen_ids = self.__getPersonenIds()       
        super(Dozentenberichte, self).__init__(parent)
        self.__getPersonenIds()
    """
    Dozentenberichte - __getPersonenIds
    Funktion zum abrufen und speichern der PersonenIds.
    """
    def __getPersonenIds(self):
        """
        Abrufen der PersonenIds.
        """
        cursorPersModulKostenst = cnxn.cursor()
        cursorPersModulKostenst.execute("select s.person_PersId " + 
                                        "from anlass a, stunden_modul s, person p, modul m " + 
                                        "where s.person_PersId = p.PersId " + 
                                        "and s.anlass_AnlassId = a.AnlassId " + 
                                        "and a.modul_ModulKuerzel = m.ModulKuerzel " + 
                                        "and m.kostenstelle_KostenstName = 'T IMES'")
        rowsPersModuleKostenst = cursorPersModulKostenst.fetchall()
        
        cursorPersKostenst = cnxn.cursor()
        cursorPersKostenst.execute("select PersId " + 
                                    "from person " + 
                                    "where kostenstelle_KostenstName = 'T IMES'")
        rowsPersKostenst = cursorPersKostenst.fetchall()
        """
        Speichern der PersonenIds mit Duplikaten.
        """
        rowsPersonen_Dup = []
        rowsPersonen_Dup.extend(rowsPersKostenst)
        rowsPersonen_Dup.extend(rowsPersModuleKostenst)
        """
        Herausfiltern der Duplikate und Speichern der PersonenIds ohne Duplikate.
        """
        rowsPersonen = []
        for m in rowsPersonen_Dup:
            if m not in rowsPersonen:
                rowsPersonen.append(m)
                
        self.personen_ids = [ x[0] for x in rowsPersonen ]
        """
        Konstruieren der Klasse GetDozData und Übergabe der benötigten Werte.
        """
        gdd = GetDozData(self, self.personen_ids, self.benutzerPersKuerzel)
        
"""
Klasse GetDozData
Zum Abrufen der benötigten Daten für einen Dozenten.
"""
class GetDozData():
    """
    Konstruktor der Klasse GetDozData.
    """
    def __init__(self, dozentenberichte, personen_ids, benutzerPersKuerzel):
        self.benutzerPersKuerzel = benutzerPersKuerzel
        self.dozentenberichte = dozentenberichte
        self.personen_ids = personen_ids
        self.__getDataForPerson(self.personen_ids) 
    """
    Festlegen der Kategoriekürzel und Kategorienamen der Module.
    """
    kategorien_kuerzel = ["BA A",
                      "BA B",
                      "MA",
                      "PA",
                      "EF"]
    kategorien = ["A - Bachelor : Eigene Studiengaenge",
                  "B - Bachelor: Weitere Leistungen",
                  "D - Master MSE",
                  "C - Projekt- und Bachelor-Arbeiten",
                  "E - Allgemeine Leistungen",
                  "F - Abwesenheiten und persönliche Weiterbildung"]
        
    """
    GetDozData - __getDataForPerson
    Funktion zum Abrufen der Personendaten eines Dozenten.
    """    
    def __getDataForPerson(self, personen_ids):
        """
        Schlaufe für jeden Eintrag im PersonenIds-Array und
        Abrufen des Stundentotals für die PersonenId.
        """
        for j in range(len(self.personen_ids)):
            cursorStundenTotal = cnxn.cursor()
            cursorStundenTotal.execute("select SUM(stundenModAnzahl) from stunden_modul " +
                                       "where person_PersId = ?", str(self.personen_ids[j]))
            rowsStundenTotal = cursorStundenTotal.fetchall()
            dataStundenTotal = list(rowsStundenTotal[0])
            """
            Überprüfen ob der Dozent Stunden leistet
            Fortfahren wenn ja.
            """
            if not dataStundenTotal == [None]: 
                """
                Zurücksetzen der Totale auf 0.
                """
                self.nettoStundenProKatHS = 0.00
                self.nettoStundenProKatFS = 0.00
                self.nettoStundenHS = 0.00
                self.nettoStundenFS = 0.00
                self.nettoStundenBAArbeitHS = 0.00
                self.nettoStundenBAArbeitFS = 0.00
                self.nettoStundenPAArbeitHS = 0.00
                self.nettoStundenPAArbeitFS = 0.00
                self.nettoStundenSchuljahr = 0.00
                self.stundenLehre = 0.00
                self.stundenELA = 0.00
                self.stundenDiverse = 0.00
                """
                Festlegen der Ferien und pers. Weiterbildung auf Grund nicht vorhandener 
                Datenbankdaten.
                """
                self.abwUndPersWeiterb = [["F - Abwesenheit und pers. Weiterbildung", "", "", "", ""],
                                          ['Ferien', 105, '', 105, '', 210],
                                          ['pers. Weiterbildung (Pauschale)', 84, '', 84, '', 168],
                                          ["", "", "", "", ""]]
                """
                Aufruf der Funktion __getStundenTotale mit der Personenid zum erlangen der Stundentotale.
                """
                self.__getStundenTotale(str(self.personen_ids[j]), self.kategorien_kuerzel)
                """
                Aufruf der Funktion __getPersonenData mit der PersonenId und Speicherung des Ergebnisses in einen Array.
                Der Array enthält die Personendaten welche aus der Datenbank ausgelesen werden können.
                """
                self.personDataRaw = self.__getPersonenData(str(self.personen_ids[j]))
                """
                Aufruf der Funktion __insertVariablesPersonenData mit dem oben erstellten Array und
                speicherung des Ergebnisses in einen Array. Der Array enthält alle Personendaten mit den
                Bezeichnungen etc.
                """
                self.personData = self.__insertVariablesPersonenData(self.personDataRaw)
                """
                Aufruf der Funktion __getModuls mit der PersonenId und dem Kategoriekürzel
                und Speicherung in einen für jede Kategorie separaten Array. Die Arrays enthalten alle
                Datenbankdaten der Module in den jeweiligen Kategorien.
                """
                self.bAAModulesRaw = self.__getModuls(str(self.personen_ids[j]), self.kategorien_kuerzel[0])
                self.bABModulesRaw = self.__getModuls(str(self.personen_ids[j]), self.kategorien_kuerzel[1])
                self.mAModulesRaw = self.__getModuls(str(self.personen_ids[j]), self.kategorien_kuerzel[2])
                self.pAModulesRaw = self.__getModuls(str(self.personen_ids[j]), self.kategorien_kuerzel[3])
                self.fEModulesRaw = self.__getModuls(str(self.personen_ids[j]), self.kategorien_kuerzel[4])
                """
                Aufruf der Funktion __insertVariablesModule mit dem oben erstellten Array und dem Kategorienamen und 
                dem Stundentotal. Anschliessend Speicherung in einen für jede Kategorie separaten Array. Die Array 
                enthalten die Datenbankdaten sowie alle Bezeichnungen und anderen Werte der Module in den jeweiligen
                Kategorien.
                """
                self.bAAModules = self.__insertVariablesModule(self.bAAModulesRaw, self.kategorien[0], dataStundenTotal[0])
                self.bABModules = self.__insertVariablesModule(self.bABModulesRaw, self.kategorien[1], dataStundenTotal[0])
                self.mAModules = self.__insertVariablesModule(self.mAModulesRaw, self.kategorien[2], dataStundenTotal[0])
                self.pAModules = self.__insertVariablesModule(self.pAModulesRaw, self.kategorien[3], dataStundenTotal[0])
                self.fEModules = self.__insertVariablesModule(self.fEModulesRaw, self.kategorien[4], dataStundenTotal[0])
                
                """
                Aufruf der Funktion __getModulTotale mit der PersonenId und die Speicherung des Ergebnisses
                in einen Array. Dieser beinhaltet alle Datenbankdaten sowie die Bezeichnungen und alle anderen
                Werte welche für das Total nötig sind.
                """
                self.totaleData = self.__getModulTotale(str(self.personen_ids[j]))
                
                """
                Aufruf der Funktion __getSaldoData mit der PersonenId und die Speicherung des Ergebnisses
                in einen Array. Dieser beinhaltet alle Datenbankdaten sowie die Bezeichnungen und alle anderen
                Werte welche für das Saldo nötig sind.
                """
                self.saldoData = self.__getSaldoData(self.personen_ids[j])
                
                """Speichern der Arrays mit den Moduldaten in einen Array.
                """
                self.datasModule = [self.bAAModules, self.bABModules, self.mAModules, 
                                    self.pAModules, self.fEModules, self.abwUndPersWeiterb]
                """
                Festlegen der fileId mit dem Wert welcher von DozentenberichteDialog-__alleBerichte 
                oder DozentenberichteDialog-__eintelBericht erhalten wurden.
                """
                self.fileId = self.personen_ids[j]
                
                """
                Konstruieren der Klasse ShowingData und übergabe der benötigten Daten.
                """
                sd = ShowingData(self, self.fileId, self.personData, self.datasModule, self.totaleData, self.saldoData, self.benutzerPersKuerzel)
    
    """
    GetDozData - __getStundenTotale
    Funktion zum Abrufen, Berechnen und Speichern der Stundentotale.
    """
    def __getStundenTotale(self, persId, kategorien):
        """
        Abruf der Anzahl der jeweiligen Arbeiten im Herbstsemester.
        """
        cursorNettoStundenBAArbeitHS = cnxn.cursor()
        cursorNettoStundenBAArbeitHS.execute("select SUM(sm.stundenModAnzahl) from stunden_modul sm, anlass a, modul m " +
                                                   "where sm.anlass_AnlassId = a.AnlassId " +
                                                   "and a.modul_ModulKuerzel = m.ModulKuerzel " +
                                                   "and m.ModulKuerzel = 'Bachelor - BA' " +
                                                   "and sm.person_PersId = ? " +
                                                   "and a.semester_SemesterKuerzel = 'HS13'", persId)
        rowsNettoStundenproBAArbeitHS = cursorNettoStundenBAArbeitHS.fetchall()
        self.nettoStundenBAArbeitHS = list(rowsNettoStundenproBAArbeitHS[0])[0]
        
        cursorNettoStundenPAArbeitHS = cnxn.cursor()
        cursorNettoStundenPAArbeitHS.execute("select SUM(sm.stundenModAnzahl) from stunden_modul sm, anlass a, modul m " +
                                                   "where sm.anlass_AnlassId = a.AnlassId " +
                                                   "and a.modul_ModulKuerzel = m.ModulKuerzel " +
                                                   "and m.ModulKuerzel = 'Bachelor - PA' " +
                                                   "and sm.person_PersId = ? " +
                                                   "and a.semester_SemesterKuerzel = 'HS13'", persId)
        rowsNettoStundenproPAArbeitHS = cursorNettoStundenPAArbeitHS.fetchall()
        self.nettoStundenPAArbeitHS = list(rowsNettoStundenproPAArbeitHS[0])[0]
        """
        Überprüfung ob Stunden in den jeweiligen Arbeiten vorhanden sind.
        """
        if self.nettoStundenBAArbeitHS == None:
            self.nettoStundenBAArbeitHS = 0.00
        if self.nettoStundenPAArbeitHS == None:
            self.nettoStundenPAArbeitHS = 0.00
            """
            Bei den Arbeiten muss die Anzahl in Stunden umgerechnet werden:
            BA-Arbeit - 50h
            PA-Arbeit - 40h
            Ausserdem werden die Stunden dem Bereich Lehre hinzugefügt.
            """
        if not self.nettoStundenBAArbeitHS == None:
            self.nettoStundenBAArbeitHS = self.nettoStundenBAArbeitHS*50
            self.stundenLehre += self.nettoStundenBAArbeitHS
        if not self.nettoStundenPAArbeitHS == None:
            self.nettoStundenPAArbeitHS = self.nettoStundenPAArbeitHS*40
            self.stundenLehre += self.nettoStundenPAArbeitHS 
            
        """
        Abruf der Anzahl der jeweiligen Arbeiten im Frühlingssemester.
        """
        cursorNettoStundenBAArbeitFS = cnxn.cursor()
        cursorNettoStundenBAArbeitFS.execute("select SUM(sm.stundenModAnzahl) from stunden_modul sm, anlass a, modul m " +
                                                   "where sm.anlass_AnlassId = a.AnlassId " +
                                                   "and a.modul_ModulKuerzel = m.ModulKuerzel " +
                                                   "and m.ModulKuerzel = 'Bachelor - BA' " +
                                                   "and sm.person_PersId = ? " +
                                                   "and a.semester_SemesterKuerzel = 'FS14'", persId)
        rowsNettoStundenproBAArbeitFS = cursorNettoStundenBAArbeitFS.fetchall()
        self.nettoStundenBAArbeitFS = list(rowsNettoStundenproBAArbeitFS[0])[0]
        
        cursorNettoStundenPAArbeitFS = cnxn.cursor()
        cursorNettoStundenPAArbeitFS.execute("select SUM(sm.stundenModAnzahl) from stunden_modul sm, anlass a, modul m " +
                                                   "where sm.anlass_AnlassId = a.AnlassId " +
                                                   "and a.modul_ModulKuerzel = m.ModulKuerzel " +
                                                   "and m.ModulKuerzel = 'Bachelor - PA' " +
                                                   "and sm.person_PersId = ? " +
                                                   "and a.semester_SemesterKuerzel = 'FS14'", persId)
        rowsNettoStundenproPAArbeitFS = cursorNettoStundenPAArbeitFS.fetchall()
        self.nettoStundenPAArbeitFS = list(rowsNettoStundenproPAArbeitFS[0])[0]
        """
        Überprüfung ob Stunden in den jeweiligen Arbeiten vorhanden sind.
        """
        if self.nettoStundenBAArbeitFS == None:
            self.nettoStundenBAArbeitFS = 0.00
        if self.nettoStundenPAArbeitFS == None:
            self.nettoStundenPAArbeitFS = 0.00
            """
            Bei den Arbeiten muss die Anzahl in Stunden umgerechnet werden:
            BA-Arbeit - 50h
            PA-Arbeit - 40h
            Ausserdem werden die Stunden dem Bereich Lehre hinzugefügt.
            """
        if not self.nettoStundenBAArbeitFS == None:
            self.nettoStundenBAArbeitFS = self.nettoStundenBAArbeitFS*50
            self.stundenLehre += self.nettoStundenBAArbeitFS
        if not self.nettoStundenPAArbeitFS == None:
            self.nettoStundenPAArbeitFS = self.nettoStundenPAArbeitFS*40
            self.stundenLehre += self.nettoStundenPAArbeitFS

        self.nettoStundenHS += self.nettoStundenBAArbeitHS
        self.nettoStundenHS += self.nettoStundenPAArbeitHS
        self.nettoStundenFS += self.nettoStundenBAArbeitFS
        self.nettoStundenFS += self.nettoStundenPAArbeitFS
        
        
        """
        Abruf der Stunden pro Kategorie im Herbstsemester.
        """
        for n in range(len(kategorien)):
            cursorNettoStundenProKatHS = cnxn.cursor()
            cursorNettoStundenProKatHS.execute("select SUM(sm.stundenModAnzahl) from stunden_modul sm, anlass a, modul m " +
                                               "where sm.anlass_AnlassId = a.AnlassId " +
                                               "and sm.person_PersId = ? " +
                                               "and a.modul_ModulKuerzel = m.ModulKuerzel " +
                                               "and m.kategorie_KategorieKuerzel = ? " +
                                               "and a.semester_SemesterKuerzel = 'HS13'", persId, kategorien[n])
            rowsNettoStundenproKatHS = cursorNettoStundenProKatHS.fetchall()
            self.nettoStundenProKatHS = list(rowsNettoStundenproKatHS[0])[0] 
                     
            """
            Überprüfung ob Stunden in der Kategorie vorhanden sind.
            """
            if self.nettoStundenProKatHS == None:
                self.nettoStundenProKatHS = 0.00
                """
                Bei bestimmten Modulkategorien, umrechnung von Schulwochenlektionen in Arbeitstunden. 
                Ausserdem werden die Stunden dem Bereich Lehre hinzugefügt.
                """
            else:
                if kategorien[n] == 'BA A':
                    self.nettoStundenProKatHS = self.nettoStundenProKatHS*36.8
                    self.stundenLehre += self.nettoStundenProKatHS
                if kategorien[n] == 'BA B':
                    self.nettoStundenProKatHS = self.nettoStundenProKatHS*36.8
                    self.stundenLehre += self.nettoStundenProKatHS
                if kategorien[n] == 'MA':
                    self.stundenLehre += self.nettoStundenProKatHS
                if kategorien[n] == 'PA':
                    self.nettoStundenProKatHS = 0.00       
                    
            """
            Abruf der Stunden pro Kategorie im Frühlingssemester.
            """       
            cursorNettoStundenProKatFS = cnxn.cursor()
            cursorNettoStundenProKatFS.execute("select SUM(sm.stundenModAnzahl) from stunden_modul sm, anlass a, modul m " +
                                       "where sm.anlass_AnlassId = a.AnlassId " +
                                       "and sm.person_PersId = ? " +
                                       "and a.modul_ModulKuerzel = m.ModulKuerzel " +
                                       "and m.kategorie_KategorieKuerzel = ? " +
                                       "and a.semester_SemesterKuerzel = 'FS14'", persId, kategorien[n])
            rowsNettoStundenproKatFS = cursorNettoStundenProKatFS.fetchall()
            self.nettoStundenProKatFS = list(rowsNettoStundenproKatFS[0])[0]
            
            """
            Überprüfung ob Stunden in der Kategorie vorhanden sind.
            """ 
            if self.nettoStundenProKatFS == None:
                self.nettoStundenProKatFS = 0.00
                """
                Bei bestimmten Modulkategorien, umrechnung von Schulwochenlektionen in Arbeitstunden. 
                Ausserdem werden die Stunden dem Bereich Lehre hinzugefügt.
                """
            else:
                if kategorien[n] == 'BA A':
                    self.nettoStundenProKatFS = self.nettoStundenProKatFS*36.8
                    self.stundenLehre += self.nettoStundenProKatFS
                if kategorien[n] == 'BA B':
                    self.nettoStundenProKatFS = self.nettoStundenProKatFS*36.8
                    self.stundenLehre += self.nettoStundenProKatFS
                if kategorien[n] == 'MA':
                    self.stundenLehre += self.nettoStundenProKatFS    
                if kategorien[n] == 'PA':
                    self.nettoStundenProKatFS = 0.00
                
                
            """
            Berechnen der Stundentotale.
            """
            self.nettoStundenHS += self.nettoStundenProKatHS
            self.nettoStundenFS += self.nettoStundenProKatFS
            self.nettoStundenHSMitAbw = self.nettoStundenHS + 189
            self.nettoStundenFSMitAbw = self.nettoStundenFS + 189
        self.nettoStundenSchuljahr += self.nettoStundenHS
        self.nettoStundenSchuljahr += self.nettoStundenFS
        
        """
        Abruf des Stundentotals im Bereich "ELA".
        """
        cursorStundenELA = cnxn.cursor()
        cursorStundenELA.execute("select SUM(sm.stundenModAnzahl) from stunden_modul sm, anlass a, modul m " +
                                 "where m.ModulKuerzel = 'ELA: Weiterbildung' " +
                                 "and sm.anlass_AnlassId = a.AnlassId " +
                                 "and a.modul_ModulKuerzel = m.ModulKuerzel " +
                                 "and sm.person_PersId = ? " +
                                 "or m.ModulKuerzel = 'ELA: Dienstleistungen' " +
                                 "and sm.anlass_AnlassId = a.AnlassId " +
                                 "and a.modul_ModulKuerzel = m.ModulKuerzel " +
                                 "and sm.person_PersId = ? " +
                                 "or m.ModulKuerzel = 'ELA: F&E' " +
                                 "and sm.anlass_AnlassId = a.AnlassId " +
                                 "and a.modul_ModulKuerzel = m.ModulKuerzel " +
                                 "and sm.person_PersId = ?", persId, persId, persId)
        rowsStundenELA = cursorStundenELA.fetchall()
        self.stundenELA = list(rowsStundenELA[0])[0]
        """
        Überprüfen ob im Bereich "ELA" Stunden geleistet werden.
        """
        if self.stundenELA == None:
            self.stundenELA = 0.00
        
        """
        Abruf des Stundentotals im Bereich "Diverse".
        """    
        cursorStundenDiverse = cnxn.cursor()
        cursorStundenDiverse.execute("select SUM(sm.stundenModAnzahl) from stunden_modul sm, anlass a, modul m " +
                                     "where m.ModulKuerzel = 'Fuehrung/Administration/Support' " +
                                     "and sm.anlass_AnlassId = a.AnlassId " +
                                     "and a.modul_ModulKuerzel = m.ModulKuerzel " +
                                     "and sm.person_PersId = ? " +
                                     "or m.ModulKuerzel = 'Interne-&Sonderprojekte' " +
                                     "and sm.anlass_AnlassId = a.AnlassId " +
                                     "and a.modul_ModulKuerzel = m.ModulKuerzel " +
                                     "and sm.person_PersId = ?", persId, persId)
        rowsStundenDiverse = cursorStundenDiverse.fetchall()
        self.stundenDiverse = list(rowsStundenDiverse[0])[0]
        """
        Überprüfen ob im Bereich "Diverse" Stunden geleistet werden.
        """
        if self.stundenDiverse == None:
            self.stundenDiverse = 0.00
                   
    """
    GetDozData - __getPersonenData
    Funktion zum Abruf der Personendaten eines Dozenten
    basierend auf dessen PersId.
    """    
    def __getPersonenData(self, persId):
        self.personData = [] 
        """
        Abrufen aller Personendaten des Dozenten zusammen von den tables:
        -person
        -kostenstelle
        -saldiproplanungsjahr
        """
        cursordataPers = cnxn.cursor()
        cursordataPers.execute("select p.PersNachname, p.PersVorname, p.PersNr, p.PersBeschaeftigungsgrad, "+
                                "p.PersGeburtsdatum, p.PersKuerzel, p.PersZugesBruttogehalt, k.KostenstNr, "+
                                "p.kostenstelle_KostenstName, p.PersEintritt, sppj.SPPSaldoAZStart "+
                                "from person p, saldiproplanungsjahr sppj, kostenstelle k "+
                                "where p.PersId = sppj.person_PersId "+
                                "and p.kostenstelle_KostenstName = k.KostenstName "+
                                "and p.PersId = ?", persId)
        rowsDataPerson = cursordataPers.fetchall()
        """
        Sollte der Dozent bei sppj.SPPSaldoAZStart oder k.KostenstNr und p.kostenstelle_KonstenstName
        keinen Eintrag haben wird die Abfrage ein leeres Ergebnis zurückgeben.
        Dies wird hier überprüft:
        """
        if not rowsDataPerson == []:    #saldo JA kst JA
            """
            Die Abfrage war nicht leer, das Ergebnis kann gespeichert werden.
            """
            self.dataPerson = list(rowsDataPerson[0])
            self.dataPerson.insert(11, round(float(self.nettoStundenSchuljahr), 2))
            self.personData.append(self.dataPerson)
            
        if rowsDataPerson == []:
            """
            Die Abfrage ist leer, mittels einer veränderten Abfrage wird überprüft ob der Dozent
            nur bei k.KonstenstNr und p.kostenstelle_KonstenstName keinen Eintrag hat.
            """
            cursorDataPersOhneKst = cnxn.cursor()
            cursorDataPersOhneKst.execute("select p.PersNachname, p.PersVorname, p.PersNr, p.PersBeschaeftigungsgrad, "+
                                    "p.PersGeburtsdatum, p.PersKuerzel, p.PersZugesBruttogehalt, "+
                                    "p.PersEintritt, sppj.SPPSaldoAZStart "+
                                    "from person p, saldiproplanungsjahr sppj "+
                                    "where p.PersId = sppj.person_PersId "+
                                    "and p.PersId = ?", persId)
            rowsDataPersonOhneKst = cursorDataPersOhneKst.fetchall()
            """
            Sollte der Dozent bei sppj.SPPSaldoAZStart keinen Eintrag haben
            wird die Abfrage ein leeres Ergebnis zurückgeben.
            Dies wird hier überprüft:
            """
            if not rowsDataPersonOhneKst == []: #Saldo JA Kst NEIN
                """
                Die Abfrage war nicht leer, der Dozent verfügt nur bei k.KostenstelleNr und
                p.kostenstelle_KostenstName über keinen Eintrag. Diese Werte werden auf "nA" gesetzt und 
                das Ergebnis kann gespeichert werden.
                """
                self.dataPersonOhneKst = list(rowsDataPersonOhneKst[0])
                self.kostenstelleNr = "nA"
                self.kostenstelleName = "nA"
                self.dataPersonOhneKst.insert(7, self.kostenstelleNr)
                self.dataPersonOhneKst.insert(8, self.kostenstelleName)
                self.dataPersonOhneKst.insert(11, self.nettoStundenSchuljahr)
                self.personData.append(self.dataPersonOhneKst)
            """
            Die obere Abfrage ist leer, mittels einer veränderten Abfrage wird überprüft ob der Dozent
            nur bei sppj.SPPSaldoAZStart keinen Eintrag hat.
            """
            if rowsDataPersonOhneKst == []:
                cursorDataPersOhneSaldi = cnxn.cursor()
                cursorDataPersOhneSaldi.execute("select p.PersNachname, p.PersVorname, p.PersNr, p.PersBeschaeftigungsgrad, "+
                                                "p.PersGeburtsdatum, p.PersKuerzel, p.PersZugesBruttogehalt, k.KostenstNr, "+
                                                "p.kostenstelle_KostenstName, p.PersEintritt "+
                                                "from person p, kostenstelle k "+
                                                "where p.kostenstelle_KostenstName = k.KostenstName "+
                                                "and p.PersId = ?", persId)
                rowsDataPersonOhneSaldi = cursorDataPersOhneSaldi.fetchall()
                """
                Sollte der Dozent bei k.KostenstNr und p.konstenstelle_KostenstName keinen Eintrag haben
                wird die Abfrage ein leeres Ergebnis zurückgeben.
                Dies wird hier überprüft:
                """
                if not rowsDataPersonOhneSaldi == []:   #Saldi NEIN Kst JA
                    """
                    Die Abfrage war nicht leer, der Dozent verfügt nur bei sppj.SPPSaldoAZStart über keinen Eintrag. 
                    Dieser Wert werden auf "0.00 gesetzt und das Ergebnis kann gespeichert werden.
                    """
                    self.dataPersonOhneSaldi = list(rowsDataPersonOhneSaldi[0])
                    self.saldiStunden = 0.00
                    self.dataPersonOhneSaldi.insert(10, self.saldiStunden)
                    self.dataPersonOhneSaldi.insert(11, self.nettoStundenSchuljahr)
                    self.personData.append(self.dataPersonOhneSaldi)
                """
                Die obere Abfrage ist leer, der Dozent hat also weder bei p.Kostenstelle_KostenstName, k.KostenstNr
                noch bei sppj.SPPSaldoAZStart einen Eintrag. Die restlichen Daten werden abgerufen, diese Werte auf
                "nA" bzw. "0.00" gesetzt und das Ergebnis gespeichert.
                """
                if rowsDataPersonOhneSaldi == []:
                    cursorDataPersOhneBeides = cnxn.cursor()
                    cursorDataPersOhneBeides.execute("select p.PersNachname, p.PersVorname, p.PersNr, p.PersBeschaeftigungsgrad, "+
                                                    "p.PersGeburtsdatum, p.PersKuerzel, p.PersZugesBruttogehalt, "+
                                                    "p.PersEintritt "+
                                                    "from person p "+
                                                    "where p.PersId = ?", persId)
                    rowsDataPersonOhneBeides = cursorDataPersOhneBeides.fetchall()
                    
                    self.dataPersonOhneBeides = list(rowsDataPersonOhneBeides[0])
                    self.kostenstelleNr = "nA"
                    self.kostenstelleName = "nA"
                    self.saldiStunden = 0.00
                    self.dataPersonOhneBeides.insert(7, self.kostenstelleNr)
                    self.dataPersonOhneBeides.insert(8, self.kostenstelleName)
                    self.dataPersonOhneBeides.insert(10, self.saldiStunden)
                    self.dataPersonOhneBeides.insert(11, self.nettoStundenSchuljahr)
                    self.personData.append(self.dataPersonOhneBeides)
        """
        Hier werden die Daten welche aus dem table person abgerufen wurden auf ihr Vorhandensein überprüft.
        Sollte ein Wert nicht vorhanden sein, wird er auf "nA" gesetzt. Auch werden nicht benötigte Leerzeichen
        entfernt und das Geburtstag- und Eintrittsdatum richtig formatiert.
        """
        for m in range(len(self.personData)):
            self.personData = self.personData[m]
            for n in range(len(self.personData)):
                if self.personData[n] == None:
                    self.dataString = "nA"
                    del self.personData[n]
                    self.personData.insert(n, self.dataString)
                else:
                    if type(self.personData[n]) == unicode:
                        self.dataString = self.personData[n].strip()
                        del self.personData[n]
                        self.personData.insert(n, self.dataString)
                    else:
                        self.dataString = self.personData[n]
                        del self.personData[n]
                        self.personData.insert(n, self.dataString)
            if not self.personData[4] == "nA":
                self.GeburtsdatumProperFormat = datetime.strptime(str(self.personData[4]), '%Y-%m-%d').strftime('%d.%m.%Y')
                del self.personData[4]
                self.personData.insert(4, self.GeburtsdatumProperFormat)
            if not self.personData[9] == "nA":
                self.EintrittProperFormat = datetime.strptime(str(self.personData[9]), '%Y-%m-%d').strftime('%d.%m.%Y')
                del self.personData[9]
                self.personData.insert(9, self.EintrittProperFormat)
        return self.personData
    
    """
    GetDozData - __insertVariablesPersonenData
    Funktion zum Hinzufügen von berechnete oder festgelegten Werten sowie zur Darstellung benötigte leere
    Einträge zu den Personendaten.
    """
    def __insertVariablesPersonenData(self, data): 
        """
        Festlegen der Datenbezeichnungen und festen Werten.
        """
        self.datenBez =["Name/Vorname",
                   "Personal-Nr.",
                   "BG-V(%)",
                   "Geburtsdatum",
                   "Kurzzeichen",
                   "BG-L(%)",
                   "Kostenstelle",
                   "Ferienpauschale in Stunden (bez. BG-L)",
                   "Eintritt",
                   "Weiterbildungspauschale in Stunden (bez. BG-L)",
                   "Bruttoarbeitszeit",
                   "bei BG(100%)",
                   "Bruttoarbeitszeit (bez. BG-L)",
                   "Total Stunden",
                   "Saldo-Vorjahr",
                   "Nettoarbeitszeit (bez. BG-L)",
                   "Total Stunden"]
        self.bTitel = "Leistungsplanung: 13/14 - 01. August 2013 - 31. Juli 2014"
        self.bLeer = None
        self.bBruttoarbeitszeit = 2088.66
        self.bFerienpauschale = 210.00
        self.bWeiterbildungspauschale = 168.00
        
        self.personData = data
        self.BGL = self.personData[6]
        if not self.BGL == "nA":
            self.bBruttoBezBGL = round(((self.BGL) / 100) * self.bBruttoarbeitszeit, 2)
        else: 
            self.bBruttoBezBGL = "nA"
            
        """Einfügen der berechneten oder festgelegten Werten, den Datenbezeichnungen und benötigten
        leeren Werten.
        """
        self.personData.insert(0, self.bTitel)
        y = 0
        while y < 17:
            self.personData.insert(y+1, self.bLeer)
            y += 1
        self.personData.insert(18, self.datenBez[0])
        self.personData.insert(21, self.datenBez[1])
        self.personData.insert(23, self.bLeer)
        self.personData.insert(24, self.bLeer)
        self.personData.insert(25, self.datenBez[2])
        self.personData.insert(27, self.datenBez[3])
        self.personData.insert(29, self.bLeer)
        self.personData.insert(30, self.datenBez[4])
        self.personData.insert(32, self.bLeer)
        self.personData.insert(33, self.bLeer)
        self.personData.insert(34, self.datenBez[5])
        self.personData.insert(36, self.datenBez[6])
        self.personData.insert(39, self.datenBez[7])
        self.personData.insert(40, self.bLeer)
        self.personData.insert(41, self.bLeer)
        self.personData.insert(42, self.bLeer)
        self.personData.insert(43, self.bLeer)
        self.personData.insert(44, self.bFerienpauschale)
        self.personData.insert(45, self.datenBez[8])
        self.personData.insert(47, self.bLeer)
        self.personData.insert(48, self.datenBez[9])
        self.personData.insert(49, self.bLeer)
        self.personData.insert(50, self.bLeer)
        self.personData.insert(51, self.bLeer)
        self.personData.insert(52, self.bLeer)
        self.personData.insert(53, self.bWeiterbildungspauschale)
        z = 53
        while z < 62:
            self.personData.insert(z+1, self.bLeer)
            z += 1
        
        self.personData.insert(63, self.datenBez[10])
        self.personData.insert(64, self.bBruttoarbeitszeit)
        self.personData.insert(65, self.datenBez[11])
        self.personData.insert(66, self.datenBez[12])
        self.personData.insert(67, self.bLeer)
        self.personData.insert(68, self.bLeer)
        self.personData.insert(69, self.datenBez[13])
        self.personData.insert(70, self.bLeer)
        self.personData.insert(71, self.bBruttoBezBGL)
        self.personData.insert(72, self.datenBez[14])
        self.personData.insert(74, self.bLeer)
        self.personData.insert(75, self.datenBez[15])
        self.personData.insert(76, self.bLeer)
        self.personData.insert(77, self.bLeer)
        self.personData.insert(78, self.datenBez[13])
        self.personData.insert(79, self.bLeer)
        q = 80
        while q < 89:
            self.personData.insert(q+1, self.bLeer)
            q += 1
        
        """
        Aufteilen der Personendaten in mehrere Arrays.
        """
        zeile1 = self.personData[0:9]
        zeile2 = self.personData[9:18]
        zeile3 = self.personData[18:27]
        zeile4 = self.personData[27:36]
        zeile5 = self.personData[36:45]
        zeile6 = self.personData[45:54]
        zeile7 = self.personData[54:63]
        zeile8 = self.personData[63:72]
        zeile9 = self.personData[72:81]
        zeile10 = self.personData[81:90]
        """
        Hinzufügen der oben definierten Arrays zu einem mehrdimensionalen Array.
        """
        self.arrayPersonData = []
        self.arrayPersonData.append(zeile1)
        self.arrayPersonData.append(zeile2)
        self.arrayPersonData.append(zeile3)
        self.arrayPersonData.append(zeile4)
        self.arrayPersonData.append(zeile5)
        self.arrayPersonData.append(zeile6)
        self.arrayPersonData.append(zeile7)
        self.arrayPersonData.append(zeile8)
        self.arrayPersonData.append(zeile9)
        self.arrayPersonData.append(zeile10)
        
        return self.arrayPersonData
    
    """
    GetDozData - __getModuls
    Funktion zum Abrufen der Module, in welchen der Dozent Stunden leistet in der entsprechenden Kategorie.
    """        
    def __getModuls(self, persId, kategorie):
        modulList = []
        """
        Abrufen der Module.
        """
        cursorModuls = cnxn.cursor()
        cursorModuls.execute("select m.ModulKuerzel from anlass a, stunden_modul sm, modul m "+
                              "where sm.anlass_AnlassId = a.AnlassId "+
                              "and a.modul_ModulKuerzel = m.ModulKuerzel "+
                              "and m.kategorie_KategorieKuerzel = ? "+
                              "and sm.person_PersId = ? "+
                              "group by m.ModulKuerzel", kategorie, persId)
        rowsModuls = cursorModuls.fetchall()
        """
        Überprüfen ob Module vorhanden sind.
        """
        if not rowsModuls == []:
            """
            Wenn Module vorhanden sind, speicherung des Ergebnisses.
            """
            self.module = [i[0] for i in rowsModuls]
            for n in range(len(self.module)):
                data = self.module[n].strip()
                del self.module[n]
                self.module.insert(n, data)
                modulList.append(data)
        self.module = self.__getModulStunden(persId, modulList, kategorie)
        return self.module
    
    """
    GetDozData - __getModulStunden
    Funktion zum Abrufen der Stunden im jeweiligen Modul.
    """
    def __getModulStunden(self, persId, moduls, kategorie):
        self.modulStunden = []
        self.moduleStunden = []
        """
        Für jedes Modul des betreffenden Dozenten werden die Stunden abgerufen.
        """
        for n in range(len(moduls)):
            self.modul = moduls[n]
            """
            Abruf der Stunden des Moduls im Herbstsemester.
            """
            cursorStundenModulHS = cnxn.cursor()
            cursorStundenModulHS.execute("select sm.StundenModAnzahl from modul m, anlass a, stunden_modul sm " +
                                         "where m.ModulKuerzel = a.modul_ModulKuerzel "+
                                         "and a.AnlassId = sm.anlass_AnlassId "+
                                         "and sm.person_PersId = ? " +
                                         "and m.ModulKuerzel = ? "+
                                         "and a.semester_SemesterKuerzel = 'HS13'", persId, self.modul)
            rowsStundenModulsHS = cursorStundenModulHS.fetchall()
            """
            Überprüfen ob für das Modul im Herbstsemester Stunden vorhanden sind. Wenn ja, speicherung der 
            Daten, wenn nein festlegung des Wertes auf "".
            """
            if not rowsStundenModulsHS == []:
                self.stunden = [i[0] for i in rowsStundenModulsHS]
                self.modulHS = self.stunden[0]
            else:
                self.modulHS = ""    
            
            """
            Abruf der Stunden des Moduls im Frühlingssemester.
            """    
            cursorStundenModulFS = cnxn.cursor()
            cursorStundenModulFS.execute("select sm.StundenModAnzahl from modul m, anlass a, stunden_modul sm " +
                                         "where m.ModulKuerzel = a.modul_ModulKuerzel "+
                                         "and a.AnlassId = sm.anlass_AnlassId "+
                                         "and sm.person_PersId = ? " +
                                         "and m.ModulKuerzel = ? "+
                                         "and a.semester_SemesterKuerzel = 'FS14'", persId, self.modul)
            rowsStundenModulsFS = cursorStundenModulFS.fetchall()
            """
            Überprüfen ob für das Modul im Frühlingssemester Stunden vorhanden sind. Wenn ja, speicherung der 
            Daten, wenn nein festlegung des Wertes auf "".
            """
            if not rowsStundenModulsFS == []:
                self.stunden = [i[0] for i in rowsStundenModulsFS]
                self.modulFS = self.stunden[0]
            else:
                self.modulFS = ""
            """
            Bei Modulen in bestimmten Modulkategorien, umrechnung von Schulwochenlektionen in Arbeitstunden oder
            von Anzahl Arbeiten in Stunden.
            """
            if kategorie == 'BA A':
                if not self.modulHS == "":
                    self.modulHS = self.modulHS*36.8
                if not self.modulFS == "":
                    self.modulFS = self.modulFS*36.8
            if kategorie == 'BA B':
                if not self.modulHS == "":
                    self.modulHS = self.modulHS*36.8
                if not self.modulFS == "":
                    self.modulFS = self.modulFS*36.8
            if self.modul == 'Bachelor - BA':
                if not self.modulHS == "":
                    self.modulHS = self.modulHS*50
                if not self.modulFS == "":
                    self.modulFS = self.modulFS*50
            if self.modul == 'Bachelor - PA':
                if not self.modulHS == "":
                    self.modulHS = self.modulHS*40
                if not self.modulFS == "":
                    self.modulFS = self.modulFS*40
                 
            """
            Speicherung des Ergebnisses.
            """    
            self.modulStunden = [self.modul, self.modulHS, self.modulFS]
            
            self.moduleStunden.append(self.modulStunden)
        return self.moduleStunden
    
    """
    GetDozData - __insertVariablesModule
    Funktion zum Hinzufügen von berechnete oder festgelegten Werten sowie zur Darstellung benötigte leere
    Einträge zu den Moduldaten.
    """
    def __insertVariablesModule(self, module, kategorie, total):
        """
        Festlegen der Bezeichnungen
        """
        self.bTitel = ["Bezeichnung", "HS h", "%", "FS h", "%", "SJ h" ]
        self.bKategorie = [kategorie, "", "", "", "", ""]
        """
        Festlegen einer leeren Zeile.
        """
        self.bLeer = ["", "", "", "", "" ,""]
        """
        Berechnung von Totalen.
        """
        if not module == None:
            for n in range(len(module)):
                self.stundenTotal = 0
                if not module[n][1] == '':
                    self.stundenHS = module[n][1]
                    self.stundenTotal += self.stundenHS
                    self.prozentHS = int((self.stundenHS*100)/total)
                    if self.prozentHS == 0:
                        self.prozentHS = 1
                if module[n][1] == '':
                    self.stundenHS = ''
                    self.prozentHS = ''
                if not module[n][2] == '':
                    self.stundenFS = module[n][2]
                    self.stundenTotal += self.stundenFS
                    self.prozentFS = int((self.stundenFS*100)/total)
                    if self.prozentFS == 0:
                        self.prozentFS = 1
                if module[n][2] == '':
                    self.stundenFS = ''
                    self.prozentFS = ''
                self.kat = module[n][0]
                """
                Speicherung der Daten.
                """
                self.modul = [self.kat, self.stundenHS, self.prozentHS, self.stundenFS, self.prozentFS, self.stundenTotal]
                del module[n]
                module.insert(n, self.modul)
                """
                Hinzufügen der Modulkategorien.
                """
        module.insert(0, self.bKategorie)
        if module == None:
            module = self.bKategorie
            """
            Hinzufügen der Bezeichnung oben an den Modulen.
            """
        if kategorie == "A - Bachelor : Eigene Studiengaenge":
            module.insert(0, self.bTitel)
        module.insert(len(module), self.bLeer)
        return module
    
    """
    GetDozData - __getModulTotale
    Funktion zum abrufen und berechnen des Modultotale.
    """
    def __getModulTotale(self, persId):
        """
        Festlegen der Abwesenheitsstunden, da diese nicht in der Datenbank vorhanden sind.
        """
        self.ferienProSemester = 105.00
        self.persWeiterbProSemester = 84.00
        self.stundenAbwProSemester = self.ferienProSemester + self.persWeiterbProSemester
        """
        Berechnen der Stundentotale und bei nicht vorhandensein festlegung auf 0.
        """
        self.stundenHS = (self.nettoStundenHS + self.stundenAbwProSemester)
        self.stundenFS = (self.nettoStundenFS + self.stundenAbwProSemester)
        
        self.nettoStundenSchuljahr = round(self.nettoStundenSchuljahr, 2)
        self.totalStundenSchuljMitAbw = round(self.nettoStundenSchuljahr + (self.stundenAbwProSemester*2), 2)
        if not self.stundenHS == 0.00:
            self.prozentHS = "" + str(round(((self.stundenHS*100)/self.totalStundenSchuljMitAbw), 2)) + "%"
        if self.stundenHS == 0.00:
            self.prozentHS = "0%"
        if not self.stundenFS == 0.00:
            self.prozentFS = "" + str(round(((self.stundenFS*100)/self.totalStundenSchuljMitAbw), 2)) + "%"
        if self.stundenFS == 0.00:
            self.prozentFS = "0%"
        
        self.totalStunden = ["Total", self.stundenHS, self.prozentHS, self.stundenFS, self.prozentFS, self.totalStundenSchuljMitAbw]
        
        """
        Festlegen der leeren Zeile.
        """
        self.totalLeer = []
        l = 0
        while l < 6:
            self.totalLeer.append("")
            l += 1
            
        """
        Berechnen der Prozentualen Auswertung der Stunden und bei nicht vorhandensein festlegung auf 0.
        """
        if not self.stundenLehre == 0.00:
            self.prozentLehre = "" + str(int((self.stundenLehre*100)/self.nettoStundenSchuljahr)) + "%"
        if self.stundenLehre == 0.00:
            self.prozentLehre = "0%"
        if not self.stundenELA == 0.00:
            self.prozentELA = "" + str(int((self.stundenELA*100)/self.nettoStundenSchuljahr)) + "%"
        if self.stundenELA == 0.00:
            self.prozentELA = "0%"
        if not self.stundenDiverse == 0.00:
            self.prozentDiverse = "" + str(int((self.stundenDiverse*100)/self.nettoStundenSchuljahr)) + "%"
        if self.stundenDiverse == 0.00:
            self.prozentDiverse = "0%"
        """
        Speichern der Daten.
        """
        self.totalProzBez = ["prozentuale Auslastung  bezogen auf Nettoarbeitszeit (gerundet)", "", self.nettoStundenSchuljahr, "Lehre", "ELA", "Diverse"]
        self.totalProz = ["", "", "100%", self.prozentLehre, self.prozentELA, self.prozentDiverse]
        
        modulTotale = [self.totalStunden, self.totalLeer, self.totalProzBez, self.totalProz, self.totalLeer]
        return modulTotale
    
    """
    GetDozData - __getSaldoData
    Funktion zum abrufen und berechnen der Saldodaten.
    """
    def __getSaldoData(self, persId):
        """
        Abrufen des Personenkürzel des Dozenten.
        """
        cursorDozKuerzel = cnxn.cursor()
        cursorDozKuerzel.execute("select PersKuerzel from person " + 
                                 "where PersId = ?", persId)
        rowsDozKuerzel = cursorDozKuerzel.fetchall()
        """
        Überprüfung ob der Personenkürzel vorhanden ist. Wenn nicht:
        Abfrage des Vor- und Nachnamen.
        """
        self.dozKuerzel = [i[0] for i in rowsDozKuerzel]
        if not self.dozKuerzel == [None]:
            self.dozBez = self.dozKuerzel[0]
        if self.dozKuerzel == [None]:
            cursorDozName = cnxn.cursor()
            cursorDozName.execute("select PersNachname from person " +
                                  "where PersId = ?", persId) 
            rowsDozName = cursorDozName.fetchall()
            
            self.dozName = [i[0] for i in rowsDozName]
            if not self.dozName == [None]:
                self.dozBez = self.dozName[0]
            if self.dozName == [None]:
                self.dozBez = "Dozent"
        """
        Festlegung der Datenbezeichnungen.
        """
        self.bemerkZuTaetBez = ["Bemerkungen zu Tätigkeiten:", "Besprochen am:", "", "", ""]
        """
        Speicherung der Daten.
        """
        self.bemerkZuTaetData = ["", "" + self.benutzerPersKuerzel + ":", "" + self.dozBez + ":", "", ""]
        
        """
        Festlegen einer leeren Zeile.
        """
        self.saldoLeer = []
        l = 0
        while l < 5:
            self.saldoLeer.append("")
            l += 1
        
        """
        Abrufen des Saldo per [altes Jahr].
        """
        cursorVoraussichSaldo = cnxn.cursor()
        cursorVoraussichSaldo.execute("select sppj.SPPSaldoAZStart from person p, saldiproplanungsjahr sppj " +
                                      "where p.PersId = ? " +
                                      "and p.PersId = sppj.person_PersId", persId)
        rowsVoraussichSaldo = cursorVoraussichSaldo.fetchall()
        """
        Überprüfung ob die Abfrage ein Ergebnis geliefert hat, wenn nicht festlegung auf "nA".
        """
        self.voraussichSaldoStundenAlt = [i[0] for i in rowsVoraussichSaldo]
        if not self.voraussichSaldoStundenAlt == []:
            self.voraussichSaldoStundenAlt = self.voraussichSaldoStundenAlt[0]
        if self.voraussichSaldoStundenAlt == []:
            self.voraussichSaldoStundenAlt = "nA"
        """
        Speicherung der Daten.
        """
        self.voraussichtSaldoAlt = ["Saldo per 31.07.2013", "", "", "", self.voraussichSaldoStundenAlt]
        
        self.sollArbeit = ["Sollarbeitszeit SJ 13/14", "", self.bBruttoBezBGL, "", ""]
        
        self.stundenGepl = ["Total Stunden geplant", "", self.totalStundenSchuljMitAbw]
        """
        Überprüfung, Berechnung und Speicherung der geplanten Differenz.
        """
        if not self.bBruttoBezBGL == "nA":
            self.diffGepl = self.totalStundenSchuljMitAbw-self.bBruttoBezBGL
        if self.bBruttoBezBGL == "nA":
            self.diffGepl = self.totalStundenSchuljMitAbw
            
        self.differenzGeplant = ["Differenz geplant", "", self.diffGepl, "", self.diffGepl]
        """
        Überprüfung, Berechnung und Speicherung des voraussichtlichen Saldo des neuen Jahr.
        """
        if not self.voraussichSaldoStundenAlt == "nA":
            self.voraussichSaldoStundenNeu = self.voraussichSaldoStundenAlt + self.diffGepl
        if self.voraussichSaldoStundenAlt == "nA":
            self.voraussichSaldoStundenNeu = self.diffGepl
        
        self.voraussichtSaldoNeu = ["Voraussichtlicher Saldo per 31.07.2014", "", "", "", self.voraussichSaldoStundenNeu]
        """
        Speicherung der Saldodaten.
        """
        self.saldoDaten = [self.bemerkZuTaetBez, self.bemerkZuTaetData, self.saldoLeer, self.voraussichtSaldoAlt,
                           self.saldoLeer, self.sollArbeit, self.stundenGepl, self.differenzGeplant, self.voraussichtSaldoNeu]
        return self.saldoDaten

"""
Klasse ShowingData
Zum Darstellen der in GetDozData abgerufenen Daten.
"""
class ShowingData():
    """
    Konstruktor der Klasse ShowingData.
    """
    def __init__(self, getDozData, fileId, datasPerson, datasModule, datasTotal, datasSaldo, benutzerPersKuerzel):
        self.benutzerPersKuerzel = benutzerPersKuerzel
        self.getDozData = getDozData
        self.fileId = str(fileId)
        self.datasPerson = datasPerson
        self.datasModule = datasModule
        self.datasTotal = datasTotal
        self.datasSaldo = datasSaldo
        self.__getFileName(self.fileId)
        self.__setFormat()
        self.__showData(self.datasPerson, self.datasModule, self.datasTotal, self.datasSaldo)
    
    """
    ShowingData - __setFormat
    Funktion zum festlegen der Tabellenformate.
    """    
    def __setFormat(self):
        """
        --Formatierung Personendaten
        Festlegen der Spaltenbreite, Zeilenhöhe und Tabellenhöhe.
        """
        self.colWidthsPersData = (80,60,70,60,60,30,60,40,50)
        self.rowHeightsPersData = (15,5,15,15,15,15,5,15,15,15)
        self.tableHeightPersData = 130
        """ 
        --Formatierung Personendaten
        Hintergrund Titel 
        Hintergrund Bruttoarbeitszeit - Saldo-Vorjahr
        Hintergrund Ferienpauschale - Weiterbildungspauschale
        Hintergrund Stunden von Bruttoarbeitszeit(bez. BG-L)
        Schrift Titel
        Schrift Name/Vorname - Eintritt
        Schrift Name/Vorname zweites Feld
        Schrift Kostenstelle zweites Feld
        Schrift Bruttoarbeitszeit - Saldo-Vorjahr
        Schrift Personalnummer - Kurzzeichen
        Schrift BG-L - Weiterbildungspauschale
        Schrift Total Stunden(Brutto) - Total Stunden(Netto) 
        Schriftausrichtung Spalte ganz rechts
        """
        self.formatPersData = TableStyle([('BACKGROUND',(0,0),(9,0),colors.lemonchiffon),   
                                          ('BACKGROUND',(1,7),(1,8),colors.lemonchiffon),
                                          ('BACKGROUND',(8,4),(8,5),colors.lavenderblush),
                                          ('BACKGROUND',(8,7),(8,7),colors.lightblue),
                                          ('FONTNAME',(0,0),(0,0),'Helvetica-Bold'),    
                                          ('FONTNAME',(1,2),(1,5),'Helvetica-Bold'),    
                                          ('FONTNAME',(1,2),(2,2),'Helvetica-Bold'),    
                                          ('FONTNAME',(2,4),(2,4),'Helvetica-Bold'),   
                                          ('FONTNAME',(1,7),(1,8),'Helvetica-Bold'),    
                                          ('FONTNAME',(4,2),(4,3),'Helvetica-Bold'),   
                                          ('FONTNAME',(8,3),(8,5),'Helvetica-Bold'),    
                                          ('FONTNAME',(8,7),(8,8),'Helvetica-Bold'),
                                          ('ALIGN',(8,2),(8,8),'RIGHT')])
        
        """
        Der Array mit den verschiedenen Modulkategorien und den dazugehörigen Modulen wird Eintrag
        für Eintrag durchgelaufen.
        """
        self.tableHeightModData = []
        for j in range(len(self.datasModule)):
            """
            Festlegen der Tabellenhöhe.
            """
            self.tableHeight = len(self.datasModule[j]) * 15
            self.tableHeightModData.append(self.tableHeight)
        
        """
        --Formatierung Moduldaten Bachelor
        Festlegung der Spaltenbreite.
        """    
        self.colWidthsModData = (270,50,50,50,50,50)
        """
        --Formatierung Moduldaten Bachelor
        Hintergrund Kategorie
        Gitterraster ganze Tabelle ausser letzte Spalte
        Schrift Bezeichnungen
        Schrift Modulkategorie
        Schriftausrichtung Stunden und Prozente des Moduls
        """ 
        self.formatModDataBachelor = ([('BACKGROUND',(0,1),(6,1),colors.lightgrey),
                                       ('GRID',(0,0),(-1,-2),0.5,colors.black),
                                       ('FONTNAME',(0,0),(5,0),'Helvetica-Bold'),
                                       ('FONTNAME',(0,1),(0,1),'Helvetica-Bold'),
                                       ('ALIGN',(1,2),(-1,-1),'CENTER')])
        
              
        """
        --Formatierung der restlichen Moduldatas
        Hintergrund  Kategorie
        Gitterraster ganze Tabelle ausser letzte Spalte
        Schrift Modulkategorie
        Schriftausrichtung Stunden und Prozente des Moduls
        """                
        self.formatModDataRestl = ([('BACKGROUND',(0,0),(6,0),colors.lightgrey),
                                       ('GRID',(0,0),(-1,-2),0.5,colors.black),
                                       ('FONTNAME',(0,0),(0,0),'Helvetica-Bold'),
                                       ('ALIGN',(1,1),(-1,-1),'CENTER')])
        
        """
        --Formatierung des Totals
        Festlegung der Tabellenhöhe und der Spaltenbreite.
        """
        self.tableHeightTotalData = 15*len(self.datasTotal)
        self.colWidthsTotalData = (270,50,50,50,50,50)
        """
        --Formatierung des Totals
        Hintergrund  der Semestertotale
        Hintergrund des Gesamtotals
        Hintergrund prozentuale Auslastung
        Gitterraster Totale
        Rahmen um prozentuale Auslastung
        Schrift Totalbezeichnung
        Schriftausrichtung Stunden und Totale des Totals
        """
        self.formatTotalData = ([('BACKGROUND',(1,0),(4,0),colors.grey),
                                 ('BACKGROUND',(0,2),(5,3),colors.lightyellow),
                                 ('BACKGROUND',(5,0),(5,0),colors.lavenderblush),
                                 ('GRID',(0,0),(5,0),0.5,colors.black),
                                 ('BOX',(0,2),(5,3),0.5,colors.black),
                                 ('FONTNAME',(0,0),(0,0),'Helvetica-Bold'),
                                 ('ALIGN',(1,0),(5,0),'CENTER')])
        
        """
        --Formatierung des Saldos
        Festlegung der Tabellenhöhe und der Spaltenbreite.
        """
        self.tableHeightSaldoData = 15*len(self.datasTotal)
        self.colWidthsSaldoData = (200,160,50,60,50)
        """
        --Formatierung des Saldos
        Hintergrund des Besprochen am
        Hintergrund Voraussichtliches Saldo alt
        Hintergrund Sollarbeitszeit
        Hintergrund Voraussichtliches Saldo neu
        Hintergrund Sollarbeit Stunden
        Hintergrund Total Stunden geplant
        Linie unter Differenz geplant
        Rahmen um Besprochen am
        Schrift Bemerkungen zu Tätigkeiten - Voraussichtlicher Saldo neu
        """
        self.formatSaldoData = ([('BACKGROUND',(1,0),(4,1),colors.lightgrey),
                                 ('BACKGROUND',(0,3),(0,3),colors.lightyellow),
                                 ('BACKGROUND',(0,5),(0,5),colors.lightyellow),
                                 ('BACKGROUND',(0,8),(0,8),colors.lightyellow),
                                 ('BACKGROUND',(2,5),(2,5),colors.lightblue),
                                 ('BACKGROUND',(2,6),(2,6),colors.lavenderblush),
                                 ('LINEBELOW',(4,7),(4,7),0.5,colors.black),
                                 ('LINEBELOW',(4,8),(4,8),1.5,colors.black),
                                 ('BOX',(1,0),(4,1),0.5,colors.black),
                                 ('FONTNAME',(0,0),(0,8),'Helvetica-Bold')])
        
    """
    ShowingData - __getFileName
    Funktion zur Definition des Dateinamen.
    """    
    def __getFileName(self, fileId):
        """
        Abrufen des Personenkürzel des Dozenten.
        """
        cursorFilenameKuerzel = cnxn.cursor()
        cursorFilenameKuerzel.execute("select PersKuerzel from person " +
                                      "where PersId = ?", self.fileId)
        rowsFilenameKuerzel = cursorFilenameKuerzel.fetchall()
        self.persKuerzel = [i[0] for i in rowsFilenameKuerzel] 
        """
        Überprüfung ob die Abfrage des Personenkürzel ein Ergebnis lieferte.
        """
        if not self.persKuerzel == [None]:
            self.fileName = self.persKuerzel[0]
        """
        Falls die Abfrage des Personenkürzel kein Ergebnis lieferte wird der Vor-
        und Nachname abgefragt.
        """
        if self.persKuerzel == [None]:
            cursorFilenameName = cnxn.cursor()
            cursorFilenameName.execute("select PersNachname, PersVorname from person " +
                                          "where PersId = ?", self.fileId)
            rowsFilenameName = cursorFilenameName.fetchall()
            """
            Speicherung des Dateinamen.
            """
            self.persName = [i[0] for i in rowsFilenameName]
            self.fileName = str(self.persName[0]).strip()
    
    """
    ShowingData - __showData
    Funktion zum hinzugüfen der Tabelle und der Fusszeile zum Pdf.
    """        
    def __showData(self, datasPerson, datasModule, datasTotal, datasSaldo):
        """
        __showData - __drawPage
        Funktion zum Zeichnen der Fusszeile.
        """
        def __drawPage(canvas, doc):
            """
            Festlegung des Inhalts und Formats der Fusszeile, sowie Zeichnung derer.
            """
            self.date = time.strftime("%d.%m.%Y")
            canvas.saveState()
            canvas.setFillColor(gray)
            canvas.setFont('Helvetica',9)
            canvas.drawString(20, 15, "" + (self.fileName) +".pdf")
            canvas.drawString(500, 15, "Datum: %s" %(self.date))
            canvas.restoreState()
        
        """
        Festlegung des Dateinamen.
        """    
        name = "" + self.fileName + ".pdf"
        """
        Festlegung der pdf-Formatierung.
        """
        doc = SimpleDocTemplate(name, pagesize=A4, rightMargin=9,leftMargin=9,
                        topMargin=9,bottomMargin=18)
        """
        Array welcher die Elemente des pdf beinhaltet.
        """
        self.elements = []
        """
        Festlegung der Höhe des pdfs und der Totalhöhe der Elemente zur Ermittlung,
        wann ein Seitenumbruch eingefügt werden muss.
        """
        self.totalHeight = 0
        self.pageHeight = 750-9-18
        
        """
        Hinzufügen der Personendaten-Tabelle.
        """
        self.tPerson = Table(datasPerson, colWidths=self.colWidthsPersData, rowHeights=self.rowHeightsPersData, style=self.formatPersData)
        self.totalHeight += self.tableHeightPersData
        self.elements.append(self.tPerson)
        """
        Hinzufügen der Moduldaten-Tabellen.
        """    
        j = 0
        while j in range(len(datasModule)):
            """
            Hinzufügen der Bachelormoduldaten und der Höhe dieser zur Totalhöhe.
            """
            if j == 0:
                self.tBachelor = Table(datasModule[j], colWidths=self.colWidthsModData, rowHeights=15, style=self.formatModDataBachelor)
                self.totalHeight += self.tableHeightModData[j]
                """
                Überprüfung ob die Tabelle noch auf der Seite Platz hat. Wenn ja, hinzufügen, wenn nein, Seitenumbruch
                einfügen, dann Tabelle einfügen und Totalhöhe zurücksetzten.
                """
                if self.totalHeight < self.pageHeight:
                    self.elements.append(self.tBachelor)
                else:
                    self.elements.append(PageBreak())
                    self.elements.append(self.tBachelor)
                    self.totalHeigth = 0
                j += 1
                """
                Hinzufügen der restlichen Moduldaten und der Höhe dieser zur Totalhöhe.
                """
            else:
                self.tModule = Table(datasModule[j], colWidths=self.colWidthsModData, rowHeights=15, style=self.formatModDataRestl)
                self.totalHeight += self.tableHeightModData[j]
                """
                Überprüfung ob die Tabelle noch auf der Seite Platz hat. Wenn ja, hinzufügen, wenn nein, Seitenumbruch
                einfügen, dann Tabelle einfügen und Totalhöhe zurücksetzten.
                """
                if self.totalHeight < self.pageHeight:
                    self.elements.append(self.tModule)
                else:
                    self.elements.append(PageBreak())
                    self.elements.append(self.tModule)
                    self.totalHeight = 0
                j += 1
        """
        Hinzufügen der Totaldaten und der Höhe dieser zur Totalhöhe.
        """    
        self.tTotal = Table(datasTotal, colWidths=self.colWidthsTotalData, style=self.formatTotalData)
        self.totalHeight += self.tableHeightTotalData
        """
        Überprüfung ob die Tabelle noch auf der Seite Platz hat. Wenn ja, hinzufügen, wenn nein, Seitenumbruch
        einfügen, dann Tabelle einfügen und Totalhöhe zurücksetzten.
        """
        if self.totalHeight < self.pageHeight:
            self.elements.append(self.tTotal)
        else:
            self.elements.append(PageBreak())
            self.elements.append(self.tTotal)
            self.totalHeight = 0
        """
        Hinzufügen der Saldodaten und der Höhe dieser zur Totalhöhe.
        """
        self.tSaldo = Table(datasSaldo, colWidths=self.colWidthsSaldoData, style=self.formatSaldoData)
        self.totalHeight += self.tableHeightSaldoData
        """
        Überprüfung ob die Tabelle noch auf der Seite Platz hat. Wenn ja, hinzufügen, wenn nein, Seitenumbruch
        einfügen, dann Tabelle einfügen und Totalhöhe zurücksetzten.
        """
        if self.totalHeight < self.pageHeight:
            self.elements.append(self.tSaldo)
        else:
            self.elements.append(PageBreak())
            self.elements.append(self.tSaldo)  
            self.totalHeight = 0 
        
        """
        Erstellung und Speicherung des pdf
        """
        doc.build(self.elements, onFirstPage=__drawPage, onLaterPages=__drawPage)
        
            
# QScrollArea welches jedes StundenWidget beinhaltet
class PlanungstoolWidget(QScrollArea): 
    
    # Liste fuer die Kategorienamen
    kategorien = ["A - Bachelor : Eigene Studiengaenge (in Wochenlektionen)",
                  "B - Bachelor: Weitere Leistungen (in Wochenlektionen)",
                  "D - Master MSE (in Stunden)",
                  "C - Projekt- und Bachelor - Arbeiten (Anzahl Durchfuehrungen)",
                  "E & F - Allgemeine Leistungen (in Stunden)"]
    
    # Liste fuer die KategorieKuerzel
    kategorien_kuerzel = ["BA A",
                          "BA B",
                          "MA",
                          "PA",
                          "EF"]
    
    # Constructor des PlanungstoolWidgets
    def __init__(self, slider, semester, parent=None): 
        self.slider = slider
        self.semester = semester
        self.stundenWidgets = []
        self.__getPersonIds()
        super(PlanungstoolWidget, self).__init__(parent)
        self.setupUI()    
           
    # Ruft fuer jede Kategorie ein seperates StundenWidget auf
    def setupUI(self): 
        

        self.mainWidget = QWidget(self)
        layout = QGridLayout(self.mainWidget)
        self.mainWidget.setLayout(layout)
        self.setWidget(self.mainWidget)
        self.setWidgetResizable(True)
          
        # Ruft fuer jede Kategorie ein seperates StundenWidget auf
        for i in range(len(self.kategorien_kuerzel)): 
            wStundenWidget = StundenWidget(self,
                                           self.kategorien_kuerzel[i],
                                           self.kategorien[i],
                                           self.semester)
            layout.addWidget(wStundenWidget, i, 0)
            self.stundenWidgets.append(wStundenWidget)

        # Ruft syncScrollHori auf
        QObject.connect(self.slider, SIGNAL("actionTriggered(int)"), self.syncScrollHori)
        self.initSlider()
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
    def initSlider(self):
        scrollbar = self.stundenWidgets[0].getMainScrollbar()
        self.slider.setRange(scrollbar.minimum(), scrollbar.maximum())
        self.slider.setValue(scrollbar.value())
        
        self.slider.setSingleStep(scrollbar.singleStep())
        self.slider.setPageStep(scrollbar.pageStep())
        
    # Holt sich die Position des HorizontalSliders aus main() und ruft scrollYourTables mit diesem Wert auf
    def syncScrollHori(self): 
        sliderValue = self.slider.value()
        scrollbar = self.stundenWidgets[0].getMainScrollbar()

        for stdW in self.stundenWidgets:
            stdW.scrollYourTables(sliderValue)
            
    # Liest die PersonenIds aus der Datenban
    def __getPersonIds(self):
        
        self.nachnamen = {}
        
        def getName(personId):
            cursorNachname = cnxn.cursor()
            cursorNachname.execute("select PersId, PersNachname from person "+
                                   "where PersId = ?", personId)
            rowsNachname = cursorNachname.fetchall()
            for row in rowsNachname:
                self.nachnamen[row[0]] = row[1]
            self.personen.update(self.nachnamen)       
        
        cursorPersModulKostenst = cnxn.cursor()
        cursorPersModulKostenst.execute("select s.person_PersId, p.PersKuerzel, p.kostenstelle_KostenstName " + 
                                        "from anlass a, stunden_modul s, person p, modul m " + 
                                        "where s.person_PersId = p.PersId " + 
                                        "and s.anlass_AnlassId = a.AnlassId " + 
                                        "and a.modul_ModulKuerzel = m.ModulKuerzel " + 
                                        "and m.kostenstelle_KostenstName = 'T IMES'")
        rowsPersModuleKostenst = cursorPersModulKostenst.fetchall()
        
        cursorPersKostenst = cnxn.cursor()
        cursorPersKostenst.execute("select PersId, PersKuerzel, kostenstelle_KostenstName " + 
                                            "from person " + 
                                            "where kostenstelle_KostenstName = 'T IMES'")
        rowsPersKostenst = cursorPersKostenst.fetchall()
        
        rowsPersonen_Dup = []
        rowsPersonen_Dup.extend(rowsPersKostenst)
        rowsPersonen_Dup.extend(rowsPersModuleKostenst)
        
        rowsPersonen = []
        for m in rowsPersonen_Dup:
            if m not in rowsPersonen:
                rowsPersonen.append(m)
        
        self.personen_order = [ x[0] for x in rowsPersonen ] 
        self.personen_kuerzel = [ y[1] for y in rowsPersonen ]
        
        self.personen = {}  # Erstellt den Array "pers"

        for row in rowsPersonen:
            self.personen[row[0]] = row[1]
            
        person_idx = {}
        p = 0
        for personid in self.personen_order:
#             if not personen[personid]:
#                 continue
            person_idx[personid] = p
            if self.personen[personid] == None:
                getName(personid)
                p += 1
                
        self.personen_kostenstelle = {}
        
        for t in range(len(self.personen_order)):
            cursorKostenstelle = cnxn.cursor()
            cursorKostenstelle.execute("select PersId, kostenstelle_kostenstName from person "+
                                       "where PersId = ?", self.personen_order[t])
            rowsKostenstelle = cursorKostenstelle.fetchall()
            for row in rowsKostenstelle:
                self.personen_kostenstelle[row[0]] = row[1]
        
# Ruft KategorieWidget, ErfassungsWidget und KategorieWidget auf
class StundenWidget(QWidget):
    def __init__(self, planungsToolWidget, kategorie, kategorieName, semester):
        self.kategorie = kategorie
        self.kategorieName = kategorieName
        self.semester = semester
        self.planungsToolWidget = planungsToolWidget
        super(StundenWidget, self).__init__(self.planungsToolWidget.mainWidget)
        
        self.__getModulIds()
        
        self.setupWidget()
    
    # Passt die ScrollPosition der tables in ErfassungsWidget und TotaleWidget dem Wert von sliderValue an
    def scrollYourTables(self, sliderValue): 
        self.erfassungsTable.horiScroll.setValue(sliderValue)
        self.totalTable.horiScroll.setValue(sliderValue)   
         
    # Hier werden KategorieWidget, ErfassungsWidget und StundenWidget aufgerufen und dem Layout hinzugefuegt
    def setupWidget(self):
        
        layout = QGridLayout(self)
        self.setLayout(layout)
        #layout.setContentsMargins(0, 2, 0, 2)
        
        self.kategorieWidget = KategorieWidget(self.kategorieName, self)
        layout.addWidget(self.kategorieWidget, 0, 0)
        
        self.erfassungsTable = ErfassungsWidget(self.kategorie, self.semester, self)
        layout.addWidget(self.erfassungsTable, 1, 0)
        
        self.totalTable = TotaleWidget(self.kategorie, self.semester, self)
        layout.addWidget(self.totalTable, 2, 0)
        
    # Gibt die ScrollBar des Tables von ErfassungsWidget zurueck
    def getMainScrollbar(self):
        return self.erfassungsTable.horiScroll
                  
    # Liest die PersonenIds aus der Datenbank
    def __getModulIds(self):    
        cursorModulKostenst = cnxn.cursor()
        cursorModulKostenst.execute("select a.AnlassId, a.modul_ModulKuerzel " + 
                                        "from anlass a, modul m " + 
                                        "where a.modul_ModulKuerzel = m.ModulKuerzel " + 
                                        "and m.kategorie_KategorieKuerzel = ? " +
                                        "and a.semester_SemesterKuerzel = ? " 
                                        "and m.kostenstelle_KostenstName = 'T IMES'", self.semester, self.kategorie)
        rowsModulKostenst = cursorModulKostenst.fetchall()
        
        cursorModulPersKostenst = cnxn.cursor()
        cursorModulPersKostenst.execute("select a.AnlassId, a.modul_ModulKuerzel " + 
                                        "from stunden_modul s, anlass a, person p, modul m " + 
                                        "where s.person_PersId = p.PersId " + 
                                        "and s.anlass_AnlassId = a.AnlassId " + 
                                        "and a.modul_ModulKuerzel = m.ModulKuerzel " +
                                        "and a.semester_SemesterKuerzel = ? " 
                                        "and m.kategorie_KategorieKuerzel = ? " + 
                                        "and p.kostenstelle_KostenstName = 'T IMES'", self.semester, self.kategorie)
        rowsModulPersKostenst = cursorModulPersKostenst.fetchall()
        
        rowsModule_Dup = []
        rowsModule_Dup.extend(rowsModulKostenst)
        rowsModule_Dup.extend(rowsModulPersKostenst)
        
        rowsModule = []
        for n in rowsModule_Dup:
            if n not in rowsModule:
                rowsModule.append(n)
        
        self.module = {}
        self.module_order = [ int(x[0]) for x in rowsModule ]
        self.module_kuerzel = [ y[1] for y in rowsModule]
        
        for row in rowsModule:
            self.module[row[0]] = row[1]

    
    
# Widget fuer die Kategoriebezeichnung sowie die Buttons fuer das Anzeigen und Ausblenden des ErfassungsWidget    
class KategorieWidget(QWidget): 
    
    # Constructor von KategorieWidget
    def __init__(self, kategorie, parent):
        self.kategorie = kategorie
        super(KategorieWidget, self).__init__(parent)
        self.__widgetKategorie()
        
    # Erstellt __widgetKategorie
    def __widgetKategorie(self):
        
        layout = QGridLayout(self)
        self.setLayout(layout)
        layout.setContentsMargins(5, 0, 5, 2)
        
        labelKategorie = QLabel(self)
        buttonShow = QPushButton(self)
        buttonHide = QPushButton(self)
        
        labelKategorie.setText("" + self.kategorie + "")
        Font = QFont()
        Font.setPointSize(11)
        labelKategorie.setFont(Font)
        buttonShow.setText("Show")
        buttonShow.setMaximumWidth(75)
        buttonHide.setText("Hide")
        buttonHide.setMaximumWidth(75)
         
        layout.addWidget(labelKategorie, 0, 0)
        layout.addWidget(buttonShow, 0, 1)
        layout.addWidget(buttonHide, 0, 2)
        
        
# Widget fuer die Stundenerfassung
class ErfassungsWidget(QWidget):
    
    # Constructor von ErfassungsWidget
    def __init__(self, kategorie, semester, parent):
        self.stundenWidget = parent
        self.planungsToolWidget = self.stundenWidget.planungsToolWidget
        self.kategorie = kategorie
        self.semester = semester
        super(ErfassungsWidget, self).__init__(parent)
        self.__widgetTableErfassung()
    
    # Erstellt __widgetTableErfassung
    def __widgetTableErfassung(self):
        
        
        def hidden():
            table.hide()
            
        # Methode welche aufgerufen wird, sobald der Wert in einer Zelle des tables veraendert wurde
        def edited(row, column):
            newItem = table.currentItem()
            if newItem is not None:
                newStunden = newItem.text()  
                newPersId = self.planungsToolWidget.personen_order[column]
                newAnlassId = self.stundenWidget.module_order[row]   
                if newStunden == "":
                    newStunden = 0  
                    newValue = (newPersId, newAnlassId, float(newStunden))
                else:
                    newValue = (newPersId, newAnlassId, float(newStunden))
                newData.append(newValue)
                
        layout = QGridLayout(self)
        self.setLayout(layout)
        
        columns = len(self.planungsToolWidget.personen_kuerzel)
        rowsInsert = len(self.stundenWidget.module_kuerzel)
    
        table = QTableWidget(rowsInsert, columns, self)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.horiScroll = table.horizontalScrollBar()
        table.cellChanged.connect(edited)
        
        cursorInsert = cnxn.cursor()
        cursorInsert.execute("select s.person_PersId, s.anlass_AnlassId, s.StundenModAnzahl " + 
                             "from stunden_modul s, anlass a, modul m " + 
                             "where s.anlass_AnlassId = a.AnlassId and a.modul_ModulKuerzel = m.ModulKuerzel " +
                             "and a.semester_SemesterKuerzel = ? " 
                             "and m.kategorie_KategorieKuerzel = ? " + 
                             "order by person_PersId", self.semester, self.kategorie)
        
        rowsInsert = cursorInsert.fetchall()
        currentData.extend(rowsInsert)
        
        person_idx = {}
        modul_idx = {}
        
        i = 0
        for personid in self.planungsToolWidget.personen_order:
#             if not personen[personid]:
#                 continue
            person_idx[personid] = i
            if not self.planungsToolWidget.personen[personid] == None:
                if self.planungsToolWidget.personen_kostenstelle[personid] == None:
                    self.planungsToolWidget.personen_kostenstelle[personid] = "?"
                newItem = QTableWidgetItem(self.planungsToolWidget.personen_kostenstelle[personid].strip()+ 
                                           "\n" + self.planungsToolWidget.personen[personid].strip())
                table.setHorizontalHeaderItem(i, newItem)
                table.setColumnWidth(i, 100)
                i += 1
        
        j = 0
        for modulid in self.stundenWidget.module_order:
            modul_idx[modulid] = j
            item2 = QTableWidgetItem(self.stundenWidget.module[modulid].strip())
            table.setVerticalHeaderItem(j, item2)
            table.setRowHeight(j, 30)
            tableHeight = (len(self.stundenWidget.module_order) * 30)
            table.setMaximumHeight(tableHeight)
            table.setMinimumHeight(tableHeight + 80)
            j += 1
            
        for (personid, modulid, stunden) in rowsInsert:
            iPos = person_idx[personid]
            if not modul_idx.has_key(modulid):
                continue
            jPos = modul_idx[modulid]
            table.setItem(jPos, iPos, QTableWidgetItem(str(stunden)))
     
        table.verticalHeader().setFixedWidth(220)
        
        layout.addWidget(table, 0, 0)

        
              
# Widget fuer die StundenTotale              
class TotaleWidget(QWidget):
    
    # Constructor von TotaleWidget
    def __init__(self, kategorie, semester, parent):
        self.stundenWidget = parent
        self.planungsToolWidget = self.stundenWidget.planungsToolWidget
        super(TotaleWidget, self).__init__(parent)
        self.kategorie = kategorie
        self.semester = semester
        self.__widgetTableTotale()
        
    # Erstellt __widgetTableTotale   
    def __widgetTableTotale(self):
        
        def hiding():
            self.hide()
        
        layout2 = QGridLayout(self)
        self.setLayout(layout2)
        
        totale = ["Zwischentotal SWL",
                  "Zwischentotal Stunden"]
        
        columns = len(self.planungsToolWidget.personen_kuerzel)
        rows = len(totale)    
    
        table = QTableWidget(rows, columns, self)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        table.horizontalHeader().hide()
        self.horiScroll = table.horizontalScrollBar()
        table.setDisabled(True)
             
        person_idx = {}
        
        i = 0
        for personid in self.planungsToolWidget.personen_order:
            if not self.planungsToolWidget.personen[personid]:
                continue
            person_idx[personid] = i
            item = QTableWidgetItem(self.planungsToolWidget.personen[personid])
            table.setHorizontalHeaderItem(i, item)
            table.setColumnWidth(i, 100)
            i += 1

            
        for i in range(len(totale)):
            item = totale[i]
            table.setVerticalHeaderItem(i, QTableWidgetItem(str(item)))
            table.setRowHeight(i, 30)
            tableHeight = (len(totale) * 30)
            table.setMaximumHeight(tableHeight)
            table.setMinimumHeight(tableHeight)
                    
        cursor = cnxn.cursor()
        cursor.execute("select s.person_PersId, SUM(s.StundenModAnzahl) as total " + 
                       "from stunden_modul s, anlass a, modul m " + 
                       "where s.anlass_AnlassId = a.AnlassId " + 
                       "and a.modul_ModulKuerzel = m.ModulKuerzel " +
                       "and a.semester_SemesterKuerzel = ? " 
                       "and m.kategorie_KategorieKuerzel = ? " + 
                       "group by person_PersId"
                        , self.semester, self.kategorie)
        rows = cursor.fetchall()

        for (personid, stunden) in rows:
            if not person_idx.has_key(personid):
                continue
            iPos = person_idx[personid]
            item = QTableWidgetItem(str(stunden))
            table.setItem(0, iPos, item)
            
        table.verticalHeader().setFixedWidth(220)
        layout2.addWidget(table, 0, 0)      
        
# Widget fuer die Buttons "Save", "Reset" und "Close"        
class ButtonWidget(QWidget):
    
    # Constructor von ButtonWidget
    def __init__(self, parent):
        super(ButtonWidget, self).__init__(parent)
        self.buttonWidget()
          
    # Erstellt buttonWidget
    def buttonWidget(self):
        
        # Methode um update-Befehle in der Datenbank auszufuehren
        def updateDatabase(newDataPersId, newDataAnlassId, newDataStunden):
            cursorUpdate = cnxn.cursor()
            cursorUpdate.execute("update stunden_modul set stundenModAnzahl = ? " + 
                                 "where person_PersId = ? " + 
                                 "and anlass_AnlassId = ?"
                                 , (newDataStunden, newDataPersId, newDataAnlassId))
                                
            cursorUpdate.commit()
            print "Datensatz update"
             
        # Methode um insert-Befehle in der Datenbank auszufuehren
        def insertDatabase(newDataPersId, newDataAnlassId, newDataStunden):
            cursorInsert = cnxn.cursor()
            cursorInsert.execute("insert into stunden_modul(person_PersId, anlass_AnlassId, StundenModAnzahl) " + 
                                 "values(%s, %s, %s)"
                                 % (newDataPersId, newDataAnlassId, newDataStunden))
            cursorInsert.commit()
            print "Datensatz erstellt"
            
        # Methode um delete-Befehle in der Datenbank auszufuehren
        def deleteDatabase(newDataPersId, newDataAnlassId):
            cursorDelete = cnxn.cursor()
            cursorDelete.execute("delete from stunden_modul where person_PersId = '" + str(newDataPersId) + "' and anlass_AnlassId = '" + str(newDataAnlassId) + "'")
            cursorDelete.commit()
            print "Datensatz geloescht"
                
        # Diese Methode gibt die aktuellen Daten in der Datenbank zum Zeitpunkt der Speicherung zurueck
        def getDatabaseData(persId, anlassId):
            cursorInsert = cnxn.cursor()
            cursorInsert.execute("select person_PersId, anlass_AnlassId, stundenModAnzahl from stunden_modul where person_PersId =" + str(persId) + "and anlass_AnlassId =" + str(anlassId) + "")
            data = cursorInsert.fetchall()
            return data
        
        def closing():
            self.parentWidget().close()
            
        def reseting():
            python = sys.executable
            os.execl(python, python, * sys.argv)
        
        # Methode fuer das Anzeigen einer Fehlermeldung
        def errorDisplay(errorDataIds, errorDataNewStunden):
            
            errorDataUpdateData = []
            
            # Diese Methode wird aufgerufen, wenn in der Fehlermeldung der Button "Meine Aenderungen verwerfen" betaetigt wird
            def errorClose():
                dError.close()
                
            # Diese Methode wird aufgerufen, wenn in der Fehlermeldung der Button "Meine Aenderungen uebernehmen" betaetigt wird
            def errorUpdate():
                for k in range(len(errorDataUpdateData)):
                    errorDataNewDataDatensatz = errorDataUpdateData[k]
                    errorDataNewDataPersId = errorDataNewDataDatensatz[0]
                    errorDataNewDataAnlassId = errorDataNewDataDatensatz[1]
                    errorDataNewDataStunden = errorDataNewDataDatensatz[2]
                    print errorDataUpdateData[k]
                    if errorDataNewDataStunden == 0.0:
                        deleteDatabase(errorDataNewDataPersId, errorDataNewDataAnlassId)
                        errorClose()
                    else:
                        updateDatabase(errorDataNewDataPersId, errorDataNewDataAnlassId, errorDataNewDataStunden)
                        errorClose()
 
            dError = QDialog()
            layout = QGridLayout()
            dError.setLayout(layout)
            
            lInfo = QLabel()
            lInfo.setText("In der Zwischenzeit wurden Daten geaendert.")
            layout.addWidget(lInfo, 0, 0)
            
            lIhreDaten = QLabel()
            lIhreDaten.setText("Ihre eingegebenen Daten:")
            layout.addWidget(lIhreDaten, 1, 0)
                                     
            lAktuelleDaten = QLabel()
            lAktuelleDaten.setText("Die aktuellen Daten:")
            layout.addWidget(lAktuelleDaten, 1, 1)
            
            i = 0
            while i < (len(errorDataIds)):
                
                errorDataId = errorDataIds[i]
                errorDataPersId = str(errorDataId[0])
                errorDataAnlassId = str(errorDataId[1]) 
                
                cursorErrorKuerzel = cnxn.cursor()
                cursorErrorKuerzel.execute("select p.PersKuerzel, a.modul_ModulKuerzel from anlass a, person p " + 
                                           "where p.PersId = %s and a.AnlassId = %s"
                                           % (errorDataId[0], errorDataId[1]))
                errorDataPersKuerzel = cursorErrorKuerzel.fetchall()
                
                Kuerzel = errorDataPersKuerzel[0]
                person = str(Kuerzel[0])
                modul = str(Kuerzel[1])
                
                cursorErrorStunden = cnxn.cursor()
                cursorErrorStunden.execute("select stundenModAnzahl from stunden_modul " + 
                                           "where person_PersId = ? " + 
                                           "and anlass_AnlassId = ?"
                                           , (errorDataId[0], errorDataId[1]))
                errorDataStunden = cursorErrorStunden.fetchall()
                
                if errorDataStunden == []:
                    errorDataStunden.append(0.0)
                    
                if errorDataNewStunden == []:
                    errorDataNewStunden.append(0.0)
                
                newStunden = str(errorDataNewStunden[i])
                currentStunden = str(errorDataStunden[0])
                
                lErrorCurrentData = QLabel()
                lErrorCurrentData.setText("Person: %s, Modul: %s, Stunden: %.2f" % (person, modul.strip(), errorDataNewStunden[i]))               
                layout.addWidget(lErrorCurrentData, i + 2, 0)

                lErrorCurrentData = QLabel()
                lErrorCurrentData.setText("Person: %s, Modul: %s, Stunden: %s" % (person, modul.strip(), currentStunden))             
                layout.addWidget(lErrorCurrentData, i + 2, 1)
                
                errorDataUpdateDataDatensatz = [errorDataPersId, errorDataAnlassId, errorDataNewStunden[i]]
                errorDataUpdateData.append(errorDataUpdateDataDatensatz)
                
                i += 1
                
            buttonUpdate = QPushButton()
            buttonUpdate.setText("Meine Daten hochladen")
            layout.addWidget(buttonUpdate, i + 5, 0)
            
            buttonDismiss = QPushButton()
            buttonDismiss.setText("Meine Aenderungen verwerfen")
            layout.addWidget(buttonDismiss, i + 5, 1)
            
            buttonDismiss.clicked.connect(errorClose)
            buttonUpdate.clicked.connect(errorUpdate)
            
            dError.exec_()
        
        # Diese Methode wird aufgerufen, wenn der "Save"-Button betaetigt wird
        def update():
            
            errorCount = 0
             
            for j in range(len(currentData)):
                currentDataDatensatz = currentData[j]
                currentDataPersId = currentDataDatensatz[0]
                currentDataAnlassId = currentDataDatensatz[1]
                currentDataId = [(currentDataPersId, currentDataAnlassId)]
                currentDataIds.extend(currentDataId) 
              
            for i in range(len(newData)):
                newDataDatensatz = newData[i]
                newDataPersId = newDataDatensatz[0]
                newDataAnlassId = newDataDatensatz[1]
                newDataStunden = newDataDatensatz[2]
                newDataId = [(newDataPersId, newDataAnlassId)]
                
                cursorInsert = cnxn.cursor()
                cursorInsert.execute("select person_PersId, anlass_AnlassId, stundenModAnzahl " + 
                                     "from stunden_modul " + 
                                     "where person_PersId = ? " + 
                                     "and anlass_AnlassId = ?", (str(newDataPersId), str(newDataAnlassId)))
                databaseData = cursorInsert.fetchall()
                
                              
                if len(databaseData) == 1:  # databaseData existiert
                    print "databaseData existiert" + str(databaseData[0]) + ""
                    if databaseData[0] not in currentData:  # databaseData =! currentData
                        print "databaseData =! currentData oder currentData existiert nicht"
                        errorDataIds.append(newDataId[0])
                        errorDataNewStunden.append(newDataStunden)
                        errorCount += 1
                    if databaseData[0] in currentData:  # databaseData = currentData
                        print "databaseData = currentData"
                        if newDataStunden == 0.0:
                            deleteDatabase(newDataPersId, newDataAnlassId)
                        else:
                            updateDatabase(newDataPersId, newDataAnlassId, newDataStunden)
                                           
                elif not databaseData:
                    print "databaseData existiert nicht"
                    if newDataId[0] not in currentDataIds:
                        print newDataId[0]
                        print currentDataId
                        print "currentData existiert nicht"
                        insertDatabase(newDataPersId, newDataAnlassId, newDataStunden)
                    if newDataId[0] in currentDataIds:
                        print "currentData existiert"
                        print "databaseData =! currentData"
                        errorDataIds.append(newDataId[0])
                        errorDataNewStunden.append(newDataStunden)
                        errorCount += 1

            if not errorCount == 0:
                errorDisplay(errorDataIds, errorDataNewStunden)
                
        
        layoutButton = QGridLayout(self)
        self.setLayout(layoutButton)
        
        buttonSave = QPushButton(self)
        buttonSave.setText("Save")
        buttonSave.setMaximumWidth(100)
        buttonClose = QPushButton(self)
        buttonClose.setText("Close")
        buttonClose.setMaximumWidth(100)
        buttonReset = QPushButton(self)
        buttonReset.setText("Reset")
        buttonReset.setMaximumWidth(100)
        
        buttonSave.clicked.connect(update)
        buttonClose.clicked.connect(closing)
        buttonReset.clicked.connect(reseting)
        
        layoutButton.addWidget(buttonReset, 0, 0)
        layoutButton.addWidget(buttonClose, 0, 1)
        layoutButton.addWidget(buttonSave, 0, 2)
        
"""
Klasse - DozentenberichteDialog
Zum Erstellen und anzeigen des Berichts-GUI
und Aufrufen der anderen Berichtsklassen.
"""
class DozentenberichteDialog(QDialog):
    """
    Konstruktor DozentenberichteDialog.
    """
    def __init__(self, parent):
        super(DozentenberichteDialog, self).__init__(parent)
        self.setupUI()
    
    """
    DozentenberichteDialog - setupUI
    Funktion zum Erstellen des Dialogs(GUI) mit den verschiedenen Elementen.
    """     
    def setupUI(self):
        self.berWidget = QWidget()
        layout = QGridLayout()
        self.setLayout(layout)
        """
        X/Y Koordinaten des GridLayout.
        """
        x = 0
        y = 0
        """
        Erstellen der Labels.
        """
        self.lBenutzerPersKuerzel = QLabel()
        self.lBenutzerPersKuerzel.setText(u"Ihr Personenkürzel:")
        layout.addWidget(self.lBenutzerPersKuerzel, x, y)
        self.lIhreKostenst = QLabel()
        self.lIhreKostenst.setText("Ihre Kostenstelle:")
        layout.addWidget(self.lIhreKostenst, x+1, y) 
        self.lGewuenschterDoz = QLabel()
        self.lGewuenschterDoz.setText(u"Gewünschter Dozent:")
        layout.addWidget(self.lGewuenschterDoz, x+2, y)
        self.lPersKuerzel = QLabel()
        self.lPersKuerzel.setText(u"Personenkürzel")
        layout.addWidget(self.lPersKuerzel, x+3, y)
        self.lNachname = QLabel()
        self.lNachname.setText("Nachname:")
        layout.addWidget(self.lNachname, x+4, y)
        self.lVorname = QLabel()
        self.lVorname.setText("Vorname:")
        layout.addWidget(self.lVorname, x+5, y)
        """
        Erstellen der LineEdits.
        """
        self.leBenutzerPersKuerzel = QLineEdit()
        layout.addWidget(self.leBenutzerPersKuerzel, x, y+1)
        self.leIhreKostenst = QLineEdit()
        self.leIhreKostenst.setText("T IMES")
        self.leIhreKostenst.setEnabled(False)
        layout.addWidget(self.leIhreKostenst, x+1, y+1)
        self.lePersKuerzel = QLineEdit()
        layout.addWidget(self.lePersKuerzel, x+3, y+1)
        self.leNachname = QLineEdit()
        layout.addWidget(self.leNachname, x+4, y+1)
        self.leVorname = QLineEdit()
        layout.addWidget(self.leVorname, x+5, y+1)
        """
        Erstellen der Buttons.
        """
        self.bEinzelBericht = QPushButton()
        self.bEinzelBericht.setText("Bericht generieren")
        layout.addWidget(self.bEinzelBericht, x+6, y)
        self.bAlleBerichte = QPushButton()
        self.bAlleBerichte.setText("Alle Berichte generieren")
        layout.addWidget(self.bAlleBerichte, x+7, y)
        self.bClose = QPushButton()
        self.bClose.setText("Schliessen")
        layout.addWidget(self.bClose, x+7, y+1)
        """
        Aufrufen der Funktionen bei Button-Press.
        """
        self.bClose.clicked.connect(self.__close)
        self.bAlleBerichte.clicked.connect(self.__alleBerichte)
        self.bEinzelBericht.clicked.connect(self.__einzelBericht)
    
    """
    DozentenberichteDialog - __close
    Funktion zum schliessen der Anwendung.
    """    
    def __close(self):
        self.close()
    
    """
    DozentenberichteDialog - alleBerichte
    Funktion zum generieren aller Dozentenberichte.
    """    
    def __alleBerichte(self):
        """
        Abrufen der Eingabe im GUI.
        """
        self.benutzerPersKuerzel = self.leBenutzerPersKuerzel.text()
        
        """
        Überprüfen der Eingabe und eventuelles Anzeigen einer Fehlermeldung.
        """
        if self.benutzerPersKuerzel == "":
            QMessageBox.about(self, u'Kein Personenkürzel eingegeben', u'Bitte geben Sie Ihren Personenkürzel ein')
        else:
            """
            Konstruieren der Klasse Dozentenberichte und übergabe der benötigten Werte.
            """
            dzb = Dozentenberichte(self.benutzerPersKuerzel, self)
    
    """
    DozentenberichteDialog - einzelBericht
    Funktion zum erstellen eines einzelnen Dozentenberichts.
    """
    def __einzelBericht(self):
        """
        Abrufen der Eingabe im GUI
        """
        self.benutzerPersKuerzel = self.leBenutzerPersKuerzel.text()
        self.persKuerzel = self.lePersKuerzel.text()
        self.persNachname = self.leNachname.text()
        self.persVorname = self.leVorname.text()
        
        cursorBerichtEinzel = cnxn.cursor()
        cursorBerichtEinzel.execute("select PersId from person " +
                                   "where PersKuerzel = ? " +
                                   "or PersNachname = ? " +
                                   "and PersVorname = ? ", self.persKuerzel, self.persNachname, self.persVorname)
        rowsBerichtEinzel = cursorBerichtEinzel.fetchall()
        """
        Überprüfen der Eingabe und eventuelles Anzeigen einer Fehlermeldung.
        """
        if len(rowsBerichtEinzel) > 1:
            QMessageBox.about(self, u'Mehrere Einträge gefunden', u'Es wurden mehrere Einträge gefunden, bitte ändern Sie ihre Eingabe')
        if not rowsBerichtEinzel == []:
            self.persId = [i[0] for i in rowsBerichtEinzel]
            print self.persId
        if rowsBerichtEinzel == []:
            QMessageBox.about(self, 'Kein Eintrag gefunden', 'Es konnte kein Dozent mit diesen Eigenschaften gefunden werden')
        else:
            """
            Konstruieren der Klasse GetDozData und übergabe der benötigten Werte.
            """    
            gdd = GetDozData(self, self.persId, self.benutzerPersKuerzel)
            """
            Öffnen der pdf-Datei
            """
            os.system("start "+r"hsbh.pdf")
 
class StundenerfassungsDialog(QDialog):
    def __init__(self, parent):
        super(StundenerfassungsDialog, self).__init__(parent)
        self.setupUI()

    def setupUI(self):
        
        semester = ["HS13",
                    "FS14"]
        
        layout = QGridLayout()
        self.setLayout(layout)
        
        slider = QScrollBar(Qt.Horizontal)
        
        tabs = QTabWidget(self)
    
        wFruehlingsSemester = PlanungstoolWidget(slider, semester[0], self)
        wHerbstSemester = PlanungstoolWidget(slider, semester[1], self)   
        
        tabs.addTab(wFruehlingsSemester, "HS13")
        tabs.addTab(wHerbstSemester, "FS14")
        tabs.show()
        
        wButtons = ButtonWidget(self)
        
        layout.addWidget(tabs, 0, 0)
        layout.addWidget(slider, 1, 0)
        layout.addWidget(wButtons, 2, 0)
        self.setMinimumWidth(1000)
        self.setMinimumHeight(1000)
           
        wFruehlingsSemester.initSlider() 
"""
Klasse StartDialog
Zum erstellen und Anzeigen des StartDialog(GUI)
""" 
class StartDialog(QDialog):
    """
    Konstruktor StartDialog
    """
    def __init__(self, parent=None):
        super(StartDialog, self).__init__(parent)
        self.begin()
    
    """
    StartDialog - begin
    Funktion zum Erstellen des Start-Dialogs(GUI) mit den verschiedenen Elementen
    """    
    def begin(self):
        layoutBeginning = QGridLayout()
        self.setLayout(layoutBeginning)
        
        lBegin = QLabel()
        lBegin.setText(u"Möchten sie das Stundenerfassungs- oder das Detailblätter-Tool öffnen?")
        
        erfassungsButton = QPushButton()
        erfassungsButton.setText(u"Stundenerfassung")
        erfassungsButton.setMaximumWidth(400)
        
        detailButton = QPushButton()
        detailButton.setText(u"Detailblätter")
        detailButton.setMaximumWidth(150)
        
        layoutBeginning.addWidget(lBegin, 0, 1)
        layoutBeginning.addWidget(erfassungsButton, 1, 1)
        layoutBeginning.addWidget(detailButton, 1, 2)
        
        """
        Aufrufen der betreffenden Funktionen bei Button-Press:
        -Erfassungstool
        -Dozentenberichttool
        """
        erfassungsButton.clicked.connect( self.__showStundenerfassungsDialog)
        detailButton.clicked.connect( self.__showDozentenberichteDialog)
        
    """
    StartDialog - __showStundenerfassungsDialog
    Funktion zum Schliessen des StartDialogs und 
    zum Aufrufen des StundenerfassungsDialog
    """
    def __showStundenerfassungsDialog(self):
        self.close()
        sefd = StundenerfassungsDialog( self )
        sefd.show()
    
    """
    StartDialog - __showDozentenberichteDialog
    Funktion zum Schliessen des StartDialogs und 
    zum Aufrufen des DozentenberichteDialog
    """    
    def __showDozentenberichteDialog(self):
        self.close()
        dbd = DozentenberichteDialog( self )
        dbd.show()
         
        
def main():
    # Create a Qt application
    app = QApplication(sys.argv)
    
    dialog = StartDialog()
    dialog.show()
    

    # Enter Qt application main loop
    sys.exit(app.exec_())

    
if __name__ == "__main__":
    main()
    
