import request from '@/utils/request';

export function freezeExamProgressItem(orderId: number | string, examName: string, reason?: string) {
  return request({
    url: '/education/exam-progress-item/freeze',
    method: 'post',
    data: { orderId, examName, reason: reason || '' }
  });
}

export function unfreezeExamProgressItem(orderId: number | string, examName: string) {
  return request({
    url: '/education/exam-progress-item/unfreeze',
    method: 'post',
    data: { orderId, examName }
  });
}
