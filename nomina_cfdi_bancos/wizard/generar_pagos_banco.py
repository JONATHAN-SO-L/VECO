# -*- encoding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import Warning
from datetime import datetime, date
import base64
import logging
_logger = logging.getLogger(__name__)

class GenerarPagosBanco(models.TransientModel):
    _name='generar.pagos.banco'
    _description = 'GenerarPagosBanco'

    #banco_id = fields.Many2one("res.bank",string='Banco')
    banco_rfc = fields.Selection(
        selection=[('BBA830831LJ2', 'BBVA Bancomer - Cuentas distintos bancos'),
                   ('BBA830831LJ2_2', 'BBVA Bancomer - Solo cuentas de banco BBVA'),
                   ('BMN930209927', 'Banorte'),
                    ('BSM970519DU8', 'Santander - Solo cuentas de banco Santanter'),
                    ('BSM970519DU8_2', 'Santander - Cuentas distintos bancos'),
                    ('BBA940707IE1', 'Banco del Bajío'),
                    ('BNM840515VB1', 'Banamex - Dispersión "C"'),
                    ('BNM840515VB1_2', 'Banamex - Dispersión "D"'),],
        string=_('Banco de dispersión'),
    )
    dato1 = fields.Char("Código de pago")
    dato2 = fields.Char("Dato adicional 2")
    dato3 = fields.Char("Dato adicional 3")
    banamex_no_cliente = fields.Char("No. cliente")
    banamex_secuencia = fields.Char("Secuencia", default="1")
    banamex_descripcion = fields.Char("Descripción", default='Nomina')
    banamex_referencia = fields.Char("Referencia")

    file_content = fields.Binary("Archivo")
    diario_pago = fields.Many2one('account.journal', string='Cuenta de pago', domain=[('type', '=', 'bank')])
    fecha_dispersion = fields.Date("Fecha de dispersión")

    @api.multi
    def action_print_generar_pagos(self):
        file_text = []
        ctx = self._context.copy()
        active_id = ctx.get('active_id')
        active_model = ctx.get('active_model')
        str_encabezado = []
        str_sumario = []
        num_registro = 1
        num_empleados = 0
        monto_total = 0
        if active_id and active_model=='hr.payslip.run':
            record = self.env[active_model].browse(active_id)

           # if self.diario_pago.bank_id.bic == 'BBA830831LJ2' or self.diario_pago.bank_id.bic == 'BSM970519DU8' or self.diario_pago.bank_id.bic == 'BMN930209927' or self.diario_pago.bank_id.bic == 'BNM840515VB1':
            #   self.banco_rfc = self.diario_pago.bank_id.bic

              ##################################################################################
              ###################################################################################
              #encabezados 
              ###################################################################################
              ###################################################################################
            if self.banco_rfc == 'BBA830831LJ2': # Bancomer
                  data1 = '3' 
                  data2 = '40'
                  data5 = '00' # estado pago
                  data7 = '          ' # filler
            elif self.banco_rfc == 'BSM970519DU8' or self.banco_rfc == 'BSM970519DU8_2': # Santander
                  enc1 = '1'+ str(num_registro).rjust(5, '0') + 'E'
                  enc2 = datetime.now().strftime("%m%d%Y")
                  if self.diario_pago.bank_account_id.acc_number:
                     enc3 = self.diario_pago.bank_account_id.acc_number.ljust(16)
                  else:
                     enc3 = '                '
                  enc4 = self.fecha_dispersion.strftime("%m%d%Y")
                  str_encabezado.append((enc1)+(enc2)+(enc3)+(enc4))
                  num_registro += 1
            elif self.banco_rfc == 'BNM840515VB1': # Banamex "C"
                  #primer encabezado
                  enc11 = '1' #FIJO
                  enc12 = self.banamex_no_cliente.rjust(12, '0')
                  enc13 = self.fecha_dispersion.strftime('%y%m%d') #datetime.strptime(self.fecha_dispersion, '%Y-%m-%d').strftime('%d%m%y')
                  enc14 = '0001' #no. consecutivo del 1-99
                  enc15 = self.diario_pago.company_id.nombre_fiscal[0:36].ljust(36, ' ') # RAZON SOCIAL
                  enc16 = self.banamex_descripcion.ljust(20, ' ') #DESCRIPCION
                  enc17 = '05' # Pago de nomina (Pagomatico) a cuentas Banamex
                  enc18 = '                                        ' # solo para ordenes de pago
                  enc19 = 'C' # version
                  enc20 = '00' #fijo
                  str_encabezado.append((enc11)+(enc12)+(enc13)+(enc14)+(enc15)+(enc16)+(enc17)+(enc18)+(enc19)+(enc20))
            elif self.banco_rfc == 'BNM840515VB1_2': # Banamex "D"
                  #primer encabezado
                  enc11 = '1' #FIJO
                  enc12 = self.banamex_no_cliente.rjust(12, '0')
                  enc13 = self.fecha_dispersion.strftime('%y%m%d') #datetime.strptime(self.fecha_dispersion, '%Y-%m-%d').strftime('%y%m%d')
                  enc14 = '0001' #no. consecutivo del 1-99
                  enc15 = self.diario_pago.company_id.nombre_fiscal[0:36].ljust(36, ' ') # RAZON SOCIAL
                  enc16 = self.banamex_descripcion.ljust(20, ' ') #DESCRIPCION
                  enc17 = '15' # FIJO
                  enc18 = 'D' # version de layout
                  enc19 = '01' #fijo              123456789012345678    12345678901234567890
                  str_encabezado.append((enc11)+(enc12)+(enc13)+(enc14)+(enc15)+(enc16)+(enc17)+(enc18)+(enc19))

              ##################################################################################
              ###################################################################################
              #registos de detalle
              ###################################################################################
              ###################################################################################
            for payslip in record.slip_ids.filtered(lambda x: x.state!='cancel'):
                    employee = payslip.employee_id

                    if employee.tipo_pago=='transferencia' and employee.diario_pago.bank_id.bic == str(self.banco_rfc).replace('_2',''):
                        net_total = sum(payslip.line_ids.filtered(lambda x:x.code=='EFECT').mapped('total'))
                        if net_total == 0:
                            continue
                        _logger.info('empleado %s --- banco %s', employee.name, self.banco_rfc)
                        if self.banco_rfc == 'BBA830831LJ2': # Dispersión de Bancomer
                           data1 = '3'+ employee.rfc # no identificador y rfc
                           if employee.tipo_cuenta == 't_debido':      #Tipo - cuenta
                              data2 = '03'
                           elif employee.tipo_cuenta == 'cheque':
                              data2 = '01'
                           else:
                              data2 = '40'
                           if employee.no_cuenta:    #Banco - Plaza destino - No. cuenta
                               data3 = employee.no_cuenta[0:6] + '0000' + employee.no_cuenta[6:]
                           data4 = str(round(net_total,2)).replace('.','').rjust(15, '0') # monto total
                           data5 = '00' # estado pago
                           data6 = employee.name[0:40].ljust(40, ' ') # nombre del empleado
                           data7 = '          ' # fillers
                           file_text.append((data1)+(data2)+(data3)+(data4)+(data5)+(data6)+(data7))
                        elif self.banco_rfc == 'BBA830831LJ2_2': # Dispersión de Bancomer solo cuentas BBVA
                           data1 = str(num_registro).zfill(9) # número consecutivo del registro
                           data2 = employee.rfc and employee.rfc.ljust(16)[:16] or '                '  #rfc 
                           data3 = '99' # NOMINA
                           data4 = employee.no_cuenta.ljust(20) #NUMERO DE CUENTA 10 DIGITOS BANCOMER
                           data5 =  str(round(net_total,2)).split('.')[0].rjust(13, '0')
                           if net_total > 0:
                              data5b =  str(round(net_total,2)).split('.')[1].ljust(2, '0')
                           else:
                              data5b =  '00'
                           nombre_empleado = employee.name.replace('/','').replace('-','').replace('.','').replace(':','').replace('?','').replace('&','').replace('!','')
                           nombre_empleado = nombre_empleado.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('ü','u')
                           nombre_empleado = nombre_empleado.replace('Á','A').replace('É','E').replace('Í','I').replace('Ó','O').replace('Ú','U').replace('Ü','u')
                           nombre_empleado = nombre_empleado.replace('ñ','n').replace('Ñ','N')
                           data6 = nombre_empleado[0:40].ljust(40, ' ') # nombre del empleado
                           data7 = '001' # fillers
                           data8 = '001' # fillers
                           file_text.append((data1)+(data2)+(data3)+(data4)+(data5)+(data5b)+(data6)+(data7)+(data8)+'\r')
                           num_registro += 1
                        elif self.banco_rfc == 'BSM970519DU8': # Dispersión de Santander - solo cuentas santander
                           data1 = '2'
                           data2 = str(num_registro).zfill(5)
                           data3 = str(employee.no_empleado).ljust(7)
                           data4 = employee.dispersion_paterno.ljust(30)[:30]
                           data5 = employee.dispersion_materno.ljust(20)[:20]
                           data6 = employee.dispersion_nombre.ljust(30)[:30]
                           data7 = employee.no_cuenta.ljust(16)
                           data8 = str(round(net_total,2)).split('.')[0].rjust(16, '0')
                           if net_total > 0:
                              data8b =  str(round(net_total,2)).split('.')[1].ljust(2, '0')
                           else:
                              data8b =  '00'
                           #for var in data8b:
                           #   _logger.info('total %s', var)
                           data9 = self.dato1 or '' #'01'
                           file_text.append((data1)+(data2)+(data3)+(data4)+(data5)+(data6)+(data7)+(data8)+(data8b)+(data9))
                           num_registro += 1
                        elif self.banco_rfc == 'BSM970519DU8_2': # Dispersión de Santander - distintos bancos
                           data1 = '2'
                           data2 = str(num_registro).zfill(5)
                           data3 = employee.name[0:50].ljust(50, ' ')
                           if employee.tipo_cuenta == 't_debido':
                              data4 = '02'
                           elif employee.tipo_cuenta == 'cheques':
                              data4 = '01'
                           elif employee.tipo_cuenta == 'c_ahorro':
                              data4 = '40'
                           data5 = employee.no_cuenta.ljust(20)
                           data6 = str(round(net_total,2)).replace('.','').rjust(18, '0')
                           data7 = employee.clave_santander_banco and employee.clave_santander_banco.rjust(5, '0') or '00000'
                           data8 = employee.plaza_santander_banco and employee.plaza_santander_banco.rjust(5, '0') or '00000'
                          # data9 = self.dato1
                           file_text.append((data1)+(data2)+(data3)+(data4)+(data5)+(data6)+(data7)+(data8))
                           num_registro += 1
                        elif self.banco_rfc == 'BNM840515VB1': # Banamex "C"
                           #3 0 001 01 001 000000000000242964 03 00005256781834028297 TRANSFER11      SALBADOR,SANTIAGO/     000000
                           data1 = '3'
                           data2 = '0'
                           data3 = '001'
                           data6 =  str(round(net_total,2)).split('.')[0].rjust(16, '0')
                           if net_total > 0:
                              data6a =  str(round(net_total,2)).split('.')[1].ljust(2, '0')
                           else:
                              data6a =  '00'
                           data7 = '01' # tipo de cuenta de abono 
                                        # 01: Cheques / CLABE
                                        # 03=Plásticos
                                        # 04=Orden de pago
                                        # 15=Cuenta concentradora
                           data8 = employee.no_cuenta.rjust(20, '0')
                           data9 = (str(num_registro)).rjust(10, '0')
                           data9a = '                              '
                           if not employee.dispersion_nombre or not employee.dispersion_paterno:
                               raise Warning("Falta nombre y/o apellido paterno para el empleado %s.", employee.name)
                           if employee.dispersion_materno:
                              nombre_empleado = employee.dispersion_nombre + ',' + employee.dispersion_paterno + '/' + employee.dispersion_materno
                           else:
                              nombre_empleado = employee.dispersion_nombre + ',' + employee.dispersion_paterno + '/'
                           nombre_empleado = nombre_empleado.replace('-','').replace('.','').replace(':','').replace('?','').replace('&','').replace('!','')
                           nombre_empleado = nombre_empleado.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
                           nombre_empleado = nombre_empleado.replace('Á','A').replace('É','E').replace('Í','I').replace('Ó','O').replace('Ú','U')
                           nombre_empleado = nombre_empleado.replace('ñ','@').replace('Ñ','@')
                           data10 = nombre_empleado[0:55].ljust(55, ' ')
                           data11 = 'TRANSFERENCIA                           '
                           data12 = '                        '
                           data15 = '    ' # clave del banco, depende de opciones
                           data16 = '       '
                           data17 = '  '
                           file_text.append((data1)+(data2)+(data3)+(data6)+(data6a)+(data7)+(data8)+(data9)+(data9a)+(data10)+(data11)+(data12)+(data15)+(data16)+(data17))
                           num_registro += 1
                        elif self.banco_rfc == 'BNM840515VB1_2': # Banamex "D"
                           #3 0 001 01 001 000000000000242964 03 00005256781834028297 TRANSFER11      SALBADOR,SANTIAGO/     000000
                           data1 = '3'
                           data2 = '0'
                           data3 = '001' # metodo pago  001: Cuentas Banamex 
                                                       #002: Interbancario 
                                                       #003: Orden de Pago.
                           data4 = '01'  #tipo de pago 01 nominna -- hay varios
                           data5 = '001'
                           data6 =  str(round(net_total,2)).split('.')[0].rjust(16, '0')
                           if net_total > 0:
                              data6a =  str(round(net_total,2)).split('.')[1].ljust(2, '0')
                           else:
                              data6a =  '00'
                           data7 = '03' # tipo de cuenta de abono 
                                        #01: Cheques, sólo válido para Pago Banamex.
                                        #03: Plásticos, válido para Pago Interbancario y Banamex.
                                        #04: Orden de Pago.
                                        #40: CLABE.
                           data8 = '0000'
                           data8a = employee.no_cuenta.ljust(16)
                           data9 = ('TRANSFER'+ str(num_registro)).ljust(16, ' ')
                           if not employee.dispersion_nombre or not employee.dispersion_paterno:
                               raise Warning("Falta nombre y/o apellido paterno para el empleado %s.", employee.name)
                           if employee.dispersion_materno:
                              nombre_empleado = employee.dispersion_nombre + ',' + employee.dispersion_paterno + '/' + employee.dispersion_materno
                           else:
                              nombre_empleado = employee.dispersion_nombre + ',' + employee.dispersion_paterno + '/'
                           nombre_empleado = nombre_empleado.replace('-','').replace('.','').replace(':','').replace('?','').replace('&','').replace('!','')
                           nombre_empleado = nombre_empleado.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
                           nombre_empleado = nombre_empleado.replace('Á','A').replace('É','E').replace('Í','I').replace('Ó','O').replace('Ú','U')
                           nombre_empleado = nombre_empleado.replace('ñ','@').replace('Ñ','@')
                           data10 = nombre_empleado[0:55].ljust(55, ' ')
                           data11 = '                                   '
                           data12 = '                                   '
                           data13 = '                                   '
                           data14 = '                                   '
                           data15 = '0000' # clave del banco, depende de opciones
                           data16 = '00'
                           data17 = '                                                                            '
                           data18 = '                                                                            '
                           #data19 = '                                                                           '
                           #data20 = '                                                  '
                           file_text.append((data1)+(data2)+(data3)+(data4)+(data5)+(data6)+(data6a)+(data7)+(data8)+(data8a)+(data9)+(data10)+(data11)+(data12)+(data13)+(data14)+(data15)+(data16)+(data17)+(data18))
                           num_registro += 1

                        num_empleados += 1
                        monto_total += round(net_total,2)

              ##################################################################################
              ###################################################################################
              #sumario
              ###################################################################################
              ###################################################################################
            if self.banco_rfc == 'BBA830831LJ2': # Bancomer
                   data1 = '3' # no identificador y rfc
                   data2 = '40'
                   data5 = '00' # estado pago
                   data7 = '          ' # filler
            elif self.banco_rfc == 'BSM970519DU8' or self.banco_rfc == 'BSM970519DU8_2':            # Santander
                   sum1 = '3'
                   sum2 = str(num_registro).rjust(5, '0')
                   sum3 = str(num_empleados).rjust(5, '0')
                   #sum4 = str(round(monto_total,2)).replace('.','').rjust(18, '0')
                   sum4 = str(round(monto_total,2)).split('.')[0].rjust(16, '0')
                   if monto_total > 0:
                      sum5 =  str(round(monto_total,2)).split('.')[1].ljust(2, '0')
                   else:
                      sum5 =  '00'
                   str_sumario.append((sum1)+(sum2)+(sum3)+(sum4)+(sum5))
            elif self.banco_rfc == 'BNM840515VB1': # Banamex "C"
                  ### segundo encabezado  2 1 001 000000000037870848 01 00000000070020012747 000258
                  enc21 = '2' #FIJO
                  enc22 = '1' #FIJO
                  enc23 = '001' #Moneda nacional
                  enc24 = str(round(monto_total,2)).split('.')[0].rjust(16, '0')
                  if monto_total > 0:
                     enc24a =  str(round(monto_total,2)).split('.')[1].ljust(2, '0')
                  else:
                     enc24a =  '00'
                  enc25 = '01' #fijo cuenta de cheques
                  if self.diario_pago.bank_account_id.acc_number:
                     enc26 = self.diario_pago.bank_account_id.acc_number[0:4] + self.diario_pago.bank_account_id.acc_number[4:].rjust(20, '0')
                  else:
                     enc26 = '                  '
                  enc27 = '                    '
                  str_encabezado.append((enc21)+(enc22)+(enc23)+(enc24)+(enc24a)+(enc25)+(enc26)+(enc27))
                  #sumario
                  #4 001 000258 000000000037870848 000001 000000000037870848
                  sum1 = '4' #FIJO
                  sum2 = '001' #Moneda nacional
                  sum3 = str(num_empleados).rjust(6, '0')
                  sum4 = str(round(monto_total,2)).split('.')[0].rjust(16, '0')
                  if monto_total > 0:
                     sum4a =  str(round(monto_total,2)).split('.')[1].ljust(2, '0')
                  else:
                     sum4a =  '00'
                  sum5 = '000001'
                  sum6 = str(round(monto_total,2)).split('.')[0].rjust(16, '0')
                  if monto_total > 0:
                     sum6a =  str(round(monto_total,2)).split('.')[1].ljust(2, '0')
                  else:
                     sum6a =  '00'
                  str_sumario.append((sum1)+(sum2)+(sum3)+(sum4)+(sum4a)+(sum5)+(sum6)+(sum6a))
            elif self.banco_rfc == 'BNM840515VB1_2': # Banamex "D"
                  ### segundo encabezado  2 1 001 000000000037870848 01 00000000070020012747 000258
                  enc21 = '2' #FIJO
                  enc22 = '1' #FIJO
                  enc23 = '001' #Moneda nacional
                  enc24 = str(round(monto_total,2)).split('.')[0].rjust(16, '0')
                  if monto_total > 0:
                     enc24a =  str(round(monto_total,2)).split('.')[1].ljust(2, '0')
                  else:
                     enc24a =  '00'
                  enc25 = '01' #fijo cuenta de cheques
                  if self.diario_pago.bank_account_id.acc_number:
                     enc26 = self.diario_pago.bank_account_id.acc_number.rjust(20, '0')
                  else:
                     enc26 = '                  '
                  enc27 = str(num_empleados).rjust(6, '0')
                  str_encabezado.append((enc21)+(enc22)+(enc23)+(enc24)+(enc24a)+(enc25)+(enc26)+(enc27))
                  #sumario
                  #4 001 000258 000000000037870848 000001 000000000037870848
                  sum1 = '4' #FIJO
                  sum2 = '001' #Moneda nacional
                  sum3 = str(num_empleados).rjust(6, '0')
                  sum4 = str(round(monto_total,2)).split('.')[0].rjust(16, '0')
                  if monto_total > 0:
                     sum4a =  str(round(monto_total,2)).split('.')[1].ljust(2, '0')
                  else:
                     sum4a =  '00'
                  sum5 = '000001'
                  sum6 = str(round(monto_total,2)).split('.')[0].rjust(16, '0')
                  if monto_total > 0:
                     sum6a =  str(round(monto_total,2)).split('.')[1].ljust(2, '0')
                  else:
                     sum6a =  '00'
                  str_sumario.append((sum1)+(sum2)+(sum3)+(sum4)+(sum4a)+(sum5)+(sum6)+(sum6a))

#            else:
#               raise Warning("Banco no compatible con la dispersión.")
        if not file_text:
            raise Warning("No hay información para generar el archivo de dispersión.")
        file_text = str_encabezado + file_text + str_sumario
        file_text = '\n'.join(file_text)
        file_text = file_text.encode()
        filename = datetime.now().strftime("%y%m-%d%H%M%S")+'.txt'
        self.write({'file_content':base64.b64encode(file_text)})
        return {
                'type' : 'ir.actions.act_url',
                'url': "/web/content/?model="+self._name+"&id=" + str(self.id) + "&field=file_content&download=true&filename="+filename+'&mimetype=text/plain',
                'target':'self',
                }