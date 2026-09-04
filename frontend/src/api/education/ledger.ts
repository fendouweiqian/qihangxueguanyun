import request from '@/utils/request';
import { EaLedgerQuery, EaLedgerVO } from './types';
import { AxiosPromise } from 'axios';

export function listLedger(query: EaLedgerQuery): AxiosPromise<EaLedgerVO[]> {
  return request({
    url: '/education/ledger/list',
    method: 'get',
    params: query
  });
}

export function getLedger(ledgerId: number | string): AxiosPromise<EaLedgerVO> {
  return request({
    url: '/education/ledger/' + ledgerId,
    method: 'get'
  });
}
