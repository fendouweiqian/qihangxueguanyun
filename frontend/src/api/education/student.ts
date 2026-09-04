import request from '@/utils/request';
import {
  EaStudentFetchNameRequest,
  EaStudentFetchNameVO,
  EaStudentForm,
  EaStudentLoginCheckRequest,
  EaStudentLoginCheckVO,
  EaStudentQuery,
  EaStudentVO
} from './types';
import { AxiosPromise } from 'axios';

export function listStudent(query: EaStudentQuery): AxiosPromise<EaStudentVO[]> {
  return request({
    url: '/education/student/list',
    method: 'get',
    params: query
  });
}

export function getStudent(studentId: number | string): AxiosPromise<EaStudentVO> {
  return request({
    url: '/education/student/' + studentId,
    method: 'get'
  });
}

export function fetchStudentName(data: EaStudentFetchNameRequest): AxiosPromise<EaStudentFetchNameVO> {
  return request({
    url: '/education/student/fetch-name',
    method: 'post',
    data
  });
}

export function checkStudentLogin(data: EaStudentLoginCheckRequest): AxiosPromise<EaStudentLoginCheckVO> {
  return request({
    url: '/education/student/login-check',
    method: 'post',
    data
  });
}

export function addStudent(data: EaStudentForm) {
  return request({
    url: '/education/student',
    method: 'post',
    data
  });
}

export function updateStudent(data: EaStudentForm) {
  return request({
    url: '/education/student',
    method: 'put',
    data
  });
}

export function delStudent(studentId: number | string | Array<number | string>) {
  return request({
    url: '/education/student/' + studentId,
    method: 'delete'
  });
}
