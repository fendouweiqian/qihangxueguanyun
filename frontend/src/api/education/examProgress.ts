import request from '@/utils/request';
import { EaExamProgressForm, EaExamProgressQuery, EaExamProgressVO } from './types';
import { AxiosPromise } from 'axios';

export function listExamProgress(query: EaExamProgressQuery): AxiosPromise<EaExamProgressVO[]> {
  return request({
    url: '/education/exam-progress/list',
    method: 'get',
    params: query
  });
}

export function getExamProgress(examProgressId: number | string): AxiosPromise<EaExamProgressVO> {
  return request({
    url: '/education/exam-progress/' + examProgressId,
    method: 'get'
  });
}

export function addExamProgress(data: EaExamProgressForm) {
  return request({
    url: '/education/exam-progress',
    method: 'post',
    data
  });
}

export function updateExamProgress(data: EaExamProgressForm) {
  return request({
    url: '/education/exam-progress',
    method: 'put',
    data
  });
}

export function delExamProgress(examProgressId: number | string | Array<number | string>) {
  return request({
    url: '/education/exam-progress/' + examProgressId,
    method: 'delete'
  });
}
