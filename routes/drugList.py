from .utils import *

class DrugList():

    def __init__(self, drugList, interventions, relations, exams, agg):
        self.drugList = drugList
        self.interventions = interventions
        self.relations = relations
        self.exams = exams
        self.agg = agg
        self.maxDoseAgg = {}
        self.alertStats = {
                'dup': 0,
                'int': 0,
                'inc': 0,
                'rea': 0,
                'maxTime': 0,
                'maxDose': 0,
                'kidney': 0,
                'liver': 0,
                'elderly': 0,
                'platelets': 0,
                'tube':0,
                'exams': 0, # kidney + liver + platelets
                'allergy': 0, # allergy + rea
            }

    def sumAlerts(self):
        self.alertStats['exams'] = self.alertStats['kidney'] + self.alertStats['liver'] + self.alertStats['platelets']
        self.alertStats['allergy'] += self.alertStats['rea']

    @staticmethod
    def sortDrugs(d):
        return remove_accents(d['drug']).lower()

    def getPrevIntervention(self, idDrug, idPrescription):
        result = {}
        for i in self.interventions:
            if i['idDrug'] == idDrug and i['status'] == 's' and int(i['idPrescription']) < idPrescription:
                if 'id' in result.keys() and int(result['id']) > int(i['id']): continue
                result = i;
        return result

    def getExistIntervention(self, idDrug, idPrescription):
        result = False
        for i in self.interventions:
            if i['idDrug'] == idDrug and int(i['idPrescription']) < idPrescription:
                result = True;
        return result

    def getIntervention(self, idPrescriptionDrug):
        result = {}
        for i in self.interventions:
            if int(i['id']) == idPrescriptionDrug:
                result = i;
        return result

    def getDrugType(self, pDrugs, source, checked=False, suspended=False):
        for pd in self.drugList:

            belong = False
            if pd[0].source is None: pd[0].source = 'Medicamentos'
            if pd[0].source != source: continue
            if source == 'Soluções': belong = True
            if checked and bool(pd[0].checked) == True and bool(pd[0].suspendedDate) == False: belong = True
            if suspended and (bool(pd[0].suspendedDate) == True): belong = True
            if (not checked and not suspended) and (bool(pd[0].checked) == False and bool(pd[0].suspendedDate) == False): belong = True

            if not belong: continue

            pdFrequency = 1 if pd[0].frequency in [33,44,55,66,99] else pd[0].frequency
            pdDoseconv = none2zero(pd[0].doseconv) * none2zero(pdFrequency)
            pdUnit = strNone(pd[2].id) if pd[2] else ''
            pdWhiteList = bool(pd[6].whiteList) if pd[6] is not None else False
            doseWeightStr = None
            expireDay = pd[10].day if pd[10] else 0

            idDrugAgg = pd[0].idDrug * 10 + expireDay
            if idDrugAgg not in self.maxDoseAgg:
                self.maxDoseAgg[idDrugAgg] = {'value': 0, 'count': 0}

            self.maxDoseAgg[idDrugAgg]['value'] += pdDoseconv
            self.maxDoseAgg[idDrugAgg]['count'] += 1

            tubeAlert = False
            alerts = []
            if not bool(pd[0].suspendedDate):
                if self.exams and pd[6]:
                    if pd[6].kidney and 'ckd' in self.exams and self.exams['ckd']['value'] and pd[6].kidney > self.exams['ckd']['value']:
                        alerts.append('Medicamento deve sofrer ajuste de posologia ou contraindicado, já que a função renal do paciente (' + str(self.exams['ckd']['value']) + ' mL/min) está abaixo de ' + str(pd[6].kidney) + ' mL/min.')
                        self.alertStats['kidney'] += 1

                    if pd[6].liver:
                        if ('tgp' in self.exams and self.exams['tgp']['value'] and float(self.exams['tgp']['value']) > pd[6].liver) or ('tgo' in self.exams and self.exams['tgo']['value'] and float(self.exams['tgo']['value']) > pd[6].liver):
                            alerts.append('Medicamento deve sofrer ajuste de posologia ou contraindicado, já que a função hepática do paciente está reduzida (acima de ' + str(pd[6].liver) + ' U/L).')
                            self.alertStats['liver'] += 1

                    if pd[6].platelets and 'plqt' in self.exams and self.exams['plqt']['value'] and pd[6].platelets > self.exams['plqt']['value']:
                        alerts.append('Medicamento contraindicado para paciente com plaquetas (' + str(self.exams['plqt']['value']) + ' plaquetas/µL) abaixo de ' + str(pd[6].platelets) + ' plaquetas/µL.')
                        self.alertStats['platelets'] += 1

                    if pd[6].elderly and self.exams['age'] > 60:
                        alerts.append('Medicamento potencialmente inapropriado para idosos, independente das comorbidades do paciente.')
                        self.alertStats['elderly'] += 1

                    if pd[6].useWeight:
                        weight = none2zero(self.exams['weight'])
                        weight = weight if weight > 0 else 1

                        doseWeight = round(pd[0].dose / float(weight),2)
                        doseWeightStr = str(doseWeight) + ' ' + pdUnit + '/Kg'

                        keyDrugKg = str(idDrugAgg)+'kg'
                        if keyDrugKg not in self.maxDoseAgg:
                            self.maxDoseAgg[keyDrugKg] = {'value': 0, 'count': 0}

                        self.maxDoseAgg[keyDrugKg]['value'] += doseWeight
                        self.maxDoseAgg[keyDrugKg]['count'] += 1 

                        if pd[6].idMeasureUnit != None and pd[6].idMeasureUnit != pdUnit:
                            doseWeightStr += ' ou ' + str(pd[0].doseconv) + ' ' + str(pd[6].idMeasureUnit) + '/Kg (faixa arredondada)'

                        if pd[6].maxDose and pd[6].maxDose < doseWeight:
                            alerts.append('Dose diária prescrita (' + str(doseWeight) + ' ' + str(pd[6].idMeasureUnit) + '/Kg) maior que a dose de alerta (' + str(pd[6].maxDose) + ' ' + str(pd[6].idMeasureUnit) + '/Kg) usualmente recomendada (considerada a dose diária independente da indicação).')
                            self.alertStats['maxDose'] += 1

                        if pd[6].maxDose and self.maxDoseAgg[keyDrugKg]['count'] > 1 and pd[6].maxDose < self.maxDoseAgg[keyDrugKg]['value']:
                            alerts.append('Dose diária prescrita SOMADA (' + str(self.maxDoseAgg[keyDrugKg]['value']) + ' ' + str(pd[6].idMeasureUnit) + '/Kg) maior que a dose de alerta (' + str(pd[6].maxDose) + ' ' + str(pd[6].idMeasureUnit) + '/Kg) usualmente recomendada (considerada a dose diária independente da indicação).')
                            self.alertStats['maxDose'] += 1

                    else:

                        if pd[6].maxDose and pd[6].maxDose < pdDoseconv:
                            alerts.append('Dose diária prescrita (' + str(pdDoseconv) + ' ' + str(pd[6].idMeasureUnit) + ') maior que a dose de alerta (' + str(pd[6].maxDose) + ' ' + str(pd[6].idMeasureUnit) + ') usualmente recomendada (considerada a dose diária independente da indicação).')
                            self.alertStats['maxDose'] += 1

                        if pd[6].maxDose and self.maxDoseAgg[idDrugAgg]['count'] > 1 and pd[6].maxDose < self.maxDoseAgg[idDrugAgg]['value']:
                            alerts.append('Dose diária prescrita SOMADA (' + str(self.maxDoseAgg[idDrugAgg]['value']) + ' ' + str(pd[6].idMeasureUnit) + ') maior que a dose de alerta (' + str(pd[6].maxDose) + ' ' + str(pd[6].idMeasureUnit) + ') usualmente recomendada (considerada a dose diária independente da indicação).')
                            self.alertStats['maxDose'] += 1

                if pd[6] and pd[6].tube and pd[0].tube:
                    alerts.append('Medicamento contraindicado via sonda (' + strNone(pd[0].route) + ')')
                    self.alertStats['tube'] += 1
                    tubeAlert = True

                if pd[0].allergy == 'S':
                    alerts.append('Paciente alérgico a este medicamento.')
                    self.alertStats['allergy'] += 1

                if pd[6] and pd[6].maxTime and pd[0].period and pd[0].period > pd[6].maxTime:
                    alerts.append('Tempo de tratamento atual (' + str(pd[0].period) + ' dias) maior que o tempo máximo de tratamento (' + str(pd[6].maxTime) + ' dias) usualmente recomendado.')
                    self.alertStats['maxTime'] += 1

                if pd[0].id in self.relations:
                    for a in self.relations[pd[0].id]:
                        self.alertStats[a[:3].lower()] += 1
                        alerts.append(a)       

            pDrugs.append({
                'idPrescription': str(pd[0].idPrescription),
                'idPrescriptionDrug': str(pd[0].id),
                'idDrug': pd[0].idDrug,
                'drug': pd[1].name if pd[1] is not None else 'Medicamento ' + str(pd[0].idDrug),
                'np': pd[6].notdefault if pd[6] is not None else False,
                'am': pd[6].antimicro if pd[6] is not None else False,
                'av': pd[6].mav if pd[6] is not None else False,
                'c': pd[6].controlled if pd[6] is not None else False,
                'q': pd[6].chemo if pd[6] is not None else False,
                'alergy': bool(pd[0].allergy == 'S'),
                'allergy': bool(pd[0].allergy == 'S'),
                'whiteList': pdWhiteList,
                'doseWeight': doseWeightStr,
                'dose': pd[0].dose,
                'measureUnit': { 'value': pd[2].id, 'label': pd[2].description } if pd[2] else '',
                'frequency': { 'value': pd[3].id, 'label': pd[3].description } if pd[3] else '',
                'dayFrequency': pd[0].frequency,
                'doseconv': pd[0].doseconv,
                'time': timeValue(pd[0].interval),
                'recommendation': pd[0].notes if pd[0].notes and len(pd[0].notes.strip()) > 0 else None,
                'period': str(pd[0].period) + 'D' if pd[0].period else '',
                'periodDates': [],
                'route': pd[0].route,
                'grp_solution': pd[0].solutionGroup,
                'stage': 'ACM' if pd[0].solutionACM == 'S' else strNone(pd[0].solutionPhase) + ' x '+ strNone(pd[0].solutionTime) + ' (' + strNone(pd[0].solutionTotalTime) + ')',
                'infusion': strNone(pd[0].solutionDose) + ' ' + strNone(pd[0].solutionUnit),
                'score': str(pd[5]) if not pdWhiteList and source != 'Dietas' else '0',
                'source': pd[0].source,
                'checked': bool(pd[0].checked or pd[9] == 's'),
                'suspended': bool(pd[0].suspendedDate),
                'status': pd[0].status,
                'near': pd[0].near,
                'prevIntervention': self.getPrevIntervention(pd[0].idDrug, pd[0].idPrescription),
                'existIntervention': self.getExistIntervention(pd[0].idDrug, pd[0].idPrescription),
                'intervention': self.getIntervention(pd[0].id),
                'alerts': alerts,
                'tubeAlert': tubeAlert,
                'notes': pd[7],
                'prevNotes': pd[8]
            })
        return pDrugs

    def sortWhiteList(self, pDrugs):
        result = [p for p in pDrugs if p['whiteList'] is False]
        result.extend([p for p in pDrugs if p['whiteList']])
        return result

    def getInfusionList(self):
        result = {}
        for pd in self.drugList:
            if pd[0].solutionGroup and pd[0].source == 'Soluções':
                
                pdID = pd[0].idPrescription
                pdGroup = pd[0].solutionGroup

                if not pdID in result:
                    result[pdID] = {}
                if not pdGroup in result[pdID].keys():
                    result[pdID][pdGroup] = {'totalVol' : 0, 'amount': 0, 'vol': 0, 'speed': 0, 'unit': 'ml'}

                pdDose = pd[0].dose

                if pd[6] and pd[6].amount and pd[6].amountUnit:
                    result[pdID][pdGroup]['vol'] = pdDose
                    result[pdID][pdGroup]['amount'] = pd[6].amount
                    result[pdID][pdGroup]['unit'] = pd[6].amountUnit

                    if pd[2].id.lower() != 'ml' and pd[2].id.lower() == pd[6].amountUnit.lower():
                        result[pdID][pdGroup]['vol'] = pdDose = round(pd[0].dose / pd[6].amount,2)

                result[pdID][pdGroup]['speed'] = pd[0].solutionDose
                result[pdID][pdGroup]['totalVol'] += pdDose if pdDose else 0
                result[pdID][pdGroup]['totalVol'] = round(result[pdID][pdGroup]['totalVol'],2)

        return result

    def concilia(self, pDrugs):
        result = []
        for p in pDrugs:
            if p['idDrug'] == 0:
                p['drug'] = p['time']
            result.append(p)
        
        return result

    def conciliaList(self, pDrugs, result = []):
        for pd in pDrugs:
            existsDrug = next((d for d in result if d['idDrug'] == pd[0].idDrug), False)
            if not existsDrug:
                result.append({
                    'idPrescription': str(pd[0].idPrescription),
                    'idPrescriptionDrug': str(pd[0].id),
                    'idDrug': pd[0].idDrug,
                    'drug': pd[1].name if pd[1] is not None else 'Medicamento ' + str(pd[0].idDrug),
                    'dose': pd[0].dose,
                    'measureUnit': { 'value': pd[2].id, 'label': pd[2].description } if pd[2] else '',
                    'frequency': { 'value': pd[3].id, 'label': pd[3].description } if pd[3] else '',
                    'time': timeValue(pd[0].interval),
                })
        
        return result

    @staticmethod
    def cpoeDrugs(drugs, idPrescription):
        for d in drugs:
            drugs[drugs.index(d)]['cpoe'] = d['idPrescription']
            drugs[drugs.index(d)]['idPrescription'] = idPrescription

        drugs.sort(key=DrugList.sortDrugs)

        return drugs