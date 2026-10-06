const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const path = require('path');
const ctx = {
  config: {classes: {A: {courses: {math: {}, eng: {}}}}},
  progressData: {}, activeCourses: c => c.courses,
  getTags: (c, n, s) => ({assign_grade: 'done', assign_tags: s === 'math'
    ? ['교재 미지참', '채점 미실시'] : {'0': '오답 풀이 안함', '1': '채점 미실시'}}),
  _readNote: () => '',
  instructor: {assignments: [{classId: 'A', subject: 'math'}, {classId: 'A', subject: 'eng'}],
    ai_message_length: 'long', ai_message_target_chars: 400,
    ai_style_mode: 'warm_detail', ai_custom_prompt: 'CUSTOM'},
};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(__dirname, 'public/v2.6.1/js/app-report.js'), 'utf8'), ctx);
const job = ctx._genCtx('A', '1', 'student');
assert.deepStrictEqual(Array.from(job.tags.assign_tags).sort(), ['교재 미지참', '채점 미실시', '오답 풀이 안함'].sort());
assert.equal(job.messageLength, 'long');
assert.equal(job.messageTargetChars, 400);
assert.equal(job.styleMode, 'warm_detail');
assert.equal(job.customPrompt, 'CUSTOM');
assert(job.items.find(i => i.subject === 'math').value.includes('교재 미지참'));
vm.runInContext("_excludeProg.add('A|math')", ctx);
const excluded = ctx._genCtx('A', '1', 'student');
assert(!excluded.tags.assign_tags.includes('교재 미지참'));
assert.equal(excluded.items.length, 1);
console.log('Multi-subject presets, excluded subjects, generation preferences passed');
