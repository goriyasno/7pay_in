# coding: utf8

import datetime
import json

import common
import db_common
import where
import recl

response.title=T("Просмотр оплат услуг в биткоинах")

def ua(h, url, cls='col-sm-4', clsA='gray-bgc'):
    return DIV(A(h, _class='block col-center button btn10 ' + clsA,
                #_style='background-color:%s;' % SKIN['bg-clr-ftr-mnu']
                 _href=url,
                )
               , _class=cls)
# готовый сектор - только ДИВ в него вставим
def sect(h, cls_bgc=' '):
    return DIV(DIV(h, _class='container'),  _class=cls_bgc)
## обрамим ее в контайнер
def mess(h, cls_c='error'):
    return DIV(DIV(DIV(h, SCRIPT("$('#tag1').scroll();"), _class='col-sm-12 ' + cls_c), _class='row'),
                   _class='container')
def err_dict(m):
    response.view = 'views/generic.html'
    return dict(h = mess(m + ', ' + 'просьба сообщить об ошибке в службу поддержки!'))

# адес тут должен быть точный
def for_addr():
    session.forget(response)
    addr = request.vars and request.vars.get('addr')
    #print 'for_addr:', addr
    if not addr or len(addr) < 24: return dict(pays=T('ошибочный адрес [%s]') % addr)

    pays = where.found_buys(db, addr)
    if len(pays)>0:
        return dict(pays=pays)

    pays=[]
    # все еще не подтвержденные
    curr, xcurr, _, = db_common.get_currs_by_addr(db, addr)
    #print curr, '\n', xcurr
    if not curr or not curr.used: return dict(pays=T('ошибочный адрес по первой букве [%s]') % addr)
    where.found_unconfirmed(db, curr, xcurr, addr, pays)


    where.found_pay_ins(db, curr, xcurr, addr, pays, None)
    if len(pays)==0: pays = T('Входов не найдено...')
    return dict(pays=pays)

#@cache.action(time_expire=request.is_local and 5 or 30, cache_model=cache.disk,
#              vars=True, public=True, lang=True)
def list():
    #print request.application
    #print request.function
    #common.page_stats(db, response['view'])
    #print request.vars
    ed_op_res = None
    ed_acc = request.vars.get('acc')
    if ed_acc:
        if len(ed_acc) > 13 and len(ed_acc) < 20:
            ed_op_id = request.vars.get('op_id')
            if ed_op_id:
                if len(ed_op_id) >10 and len(ed_op_id) < 40:
                    # заданы параметры помска платежа - делаем поиск
                    import time
                    time.sleep(3)

                    dealer_acc = db(db.dealers_accs.acc==ed_acc).select().first()
                    if dealer_acc:
                        dealer = db.dealers[ dealer_acc.dealer_id]
                        ed_op_res = LOAD('buy','income_YD', args=[ed_acc], vars={'operation_id': ed_op_id})
                    else:
                        ed_op_res = 'ed_acc not found'
                else:
                    ed_op_res = 'op_id error 2'
            else:
                ed_op_res = 'op_id error 1'
        else:
            ed_op_res = 'acc error'
    
    addr = request.args(0) or request.vars.addr
    if addr and len(addr) > 60: addr = None
    try:
        session.seeAddr = addr
    except:
        print 'list session error .seeAddr:', type(addr), addr

    response.js = "$('.go-btn').removeClass('disabled');$('#go').children('i').removeClass('fa-refresh fa-spin').addClass('fa-search');"
    
    token_system = deal_acc = curr_in = curr_out = None
    
    addr_split = addr and addr.split('>')
    if addr_split and len(addr_split) > 1:
        curr_in, xcurr_in, ecurr_in = db_common.get_currs_by_abbrev(db, addr_split[0])
        if not curr_in:
            return mess(addr_split[0] + ' curr_OUT not found')

        addr_split = addr_split[1].split(':')
        curr_out, xcurr_out, ecurr_out = db_common.get_currs_by_abbrev(db, addr_split[0])
        if not curr_out:
            return mess(addr_split[0] + ' curr_IN not found')

        addr = addr_split[1]
        deal_acc = db((db.deal_accs.acc == addr)
                     & (db.deal_accs.curr_id == curr_out.id)).select().first()

        #print curr_in.abbrev
        token_system = None
        token_key = xcurr_in.as_token
        if token_key:
            token = db.tokens[token_key]
            token_system = db.systems[token.system_id]

    import where3
    pays = []
    no_addr = where3.found_buys(db, pays, addr)
    if no_addr or len(pays)>0:
        response.view = 'where/list_buy.html'
        return dict(pays=pays, no_addr=no_addr, ed_op_res=ed_op_res)

    if token_system:
        import rpc_erachain
        curr_block = rpc_erachain.get_info(token_system.connect_url)

    no_addr = addr == "????"
    if addr and not no_addr:

        if deal_acc:
            pass
        else:
            # если адрес известен то вытащим все данные сразу
            deal_acc_addr = db(db.deal_acc_addrs.addr == addr).select().first()
            if not deal_acc_addr:
                return mess('Deals not found')
            xcurr_in = db.xcurrs[deal_acc_addr.xcurr_id ]
            curr_in = db.currs[ xcurr_in.curr_id ]
            deal_acc = db.deal_accs[ deal_acc_addr.deal_acc_id]
            curr_out = db.currs[ deal_acc.curr_id ]

        deal = db.deals[ deal_acc.deal_id ]
            
        #print deal
        payed_month = not deal.is_shop and deal_acc.payed_month or Decimal(0)
        MAX = deal.MAX_pay
        payed = deal_acc.payed or Decimal(0)
        price = deal_acc.price
        order_id = deal_acc.acc
        amo_rest_url = None
        client = db(db.clients.deal_id == deal.id).select().first()
        if client:
            curr_out = db.currs[deal_acc.curr_id]
            vvv = {'order':order_id, 'curr_out':curr_out.abbrev}

            if price and price >0 and price - payed > 0:
                # еще надо доплатить
                vvv['sum'] = price - payed
            amo_rest_url=A(T('Доплатить'), _href=URL('to_shop','index', args=[client.id],
                vars=vvv))

        import gifts_lib
        if 'to COIN' in deal.name:
            rnd = 8
        else:
            rnd = 2
        adds_mess = XML(gifts_lib.adds_mess(deal_acc, PARTNER_MIN, T, rnd))

        pays_unconf = []
        where3.found_unconfirmed(db, curr_in, xcurr_in, addr, pays_unconf)
        #print 'pays_unconf:', pays_unconf

        pays_process=[]
        where3.found_pay_ins_process(db, addr, pays_process)

        pays=[]
        where3.found_pay_ins(db, addr, pays)
        #print 'pays:', pays
        return dict( pays_unconf=pays_unconf, pays_process=pays_process, pays=pays,
            payed_month=payed_month, MAX=MAX, addr=addr,
            payed=payed, price=price, order_id=order_id, amo_rest_url=amo_rest_url,
            adds_mess = adds_mess,
            curr_in = curr_in, deal_acc = deal_acc,
            curr_out = curr_out, deal = deal, privat = False,
            )

    # сюда пришло значит ищес общий список
    pays_process=[]
    where3.found_pay_ins_process(db, addr, pays_process)
    pays=[]
    privat = where3.found_pay_ins(db, addr, pays)

    pays_unconf = []
    if not privat:
        # если мне то и все неподтв
        # все еще не подтвержденные
        for xcurr_in in db(db.xcurrs).select():
            curr_in = db.currs[xcurr_in.curr_id]
            if not curr_in or not curr_in.used: continue
            where3.found_unconfirmed(db, curr_in, xcurr_in, None, pays_unconf)

    return dict( adds_mess = None, pays_unconf=pays_unconf, pays_process=pays_process, addr = None, pays=pays, privat = privat)

def index():
    
    h = CAT(
        DIV(
            ua(SPAN(TAG.i(_class='fa fa-btc'),' ',T('Купить биткоины')), URL('to_buy', 'index')),
            ua(CAT(TAG.i(_class='fa fa-search'),' ',T('Оплатить биткоинами')), URL('deal', 'index')),
            ua(CAT(TAG.i(_class='fa fa-usd'),' ',T('Продать биткоины')), URL('to_wallet', 'index')),
            ua(T('Начало'),URL('default', 'index'),'col-sm-12'),
            _class='row')
        )
    return dict(h=h)
