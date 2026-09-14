import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from rag_library import LibraryStore, LibraryConflict


class PersonalLibraryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'library.sqlite'
        self.store = LibraryStore(self.path)
        self.payload = {'title':'Gamma', 'draft':'What is gamma?', 'pins':[],
                        'turns':[{'id':'turn1','query':'What is gamma?','pending':True}]}

    def tearDown(self):
        self.tmp.cleanup()

    def test_restart_keeps_conversation_and_bookmarks(self):
        self.store.save('chat1','conversation',0,self.payload)
        self.store.save('source1','source',0,{'title':'Greeks, p. 9','hit':{'chunk_id':'c1'}})
        reopened = LibraryStore(self.path)
        self.assertEqual(len(reopened.list()),2)
        self.assertEqual(reopened.get('chat1')['payload'],self.payload)

    def test_competing_writers_do_not_overwrite(self):
        self.store.save('chat1','conversation',0,self.payload)
        changed = {**self.payload,'title':'Renamed in tab A'}
        self.store.save('chat1','conversation',1,changed)
        with self.assertRaises(LibraryConflict):
            self.store.save('chat1','conversation',1,self.payload)
        self.assertEqual(self.store.get('chat1')['title'],changed['title'])

    def test_reply_is_persisted_without_browser_and_duplicate_request_rejected(self):
        self.store.save('chat1','conversation',0,self.payload)
        self.store.begin_turn('chat1','turn1','What is gamma?')
        with self.assertRaises(ValueError): self.store.begin_turn('chat1','turn1','What is gamma?')
        self.store.finish_turn('chat1','turn1',data={'answer':'Saved reply','citations':[]})
        payload = LibraryStore(self.path).get('chat1')['payload']
        self.assertEqual(payload['turns'][0]['data']['answer'],'Saved reply')
        self.assertFalse(payload['turns'][0]['pending'])
        self.assertEqual(payload['draft'],'')

    def test_delete_during_reply_does_not_resurrect(self):
        self.store.save('chat1','conversation',0,self.payload)
        self.store.begin_turn('chat1','turn1','What is gamma?')
        self.store.delete('chat1',2)
        self.assertIsNone(self.store.finish_turn('chat1','turn1',data={'answer':'late'}))
        with self.assertRaises(KeyError): self.store.get('chat1')
        with self.assertRaises(LibraryConflict): self.store.save('chat1','conversation',0,self.payload)

    def test_recovery_marks_interrupted_questions_without_losing_them(self):
        self.store.save('chat1','conversation',0,self.payload)
        self.store.begin_turn('chat1','turn1','What is gamma?')
        self.store.recover_pending()
        turn = self.store.get('chat1')['payload']['turns'][0]
        self.assertFalse(turn['pending'])
        self.assertIn('restarted',turn['error'])
        self.assertEqual(turn['query'],'What is gamma?')

    def test_invalid_updates_leave_saved_content_untouched(self):
        self.store.save('chat1','conversation',0,self.payload)
        for item_id, revision, payload in [('../outside',0,self.payload),('chat1',True,self.payload),
                ('chat1',1,{**self.payload,'turns':[self.payload['turns'][0]]*2}),
                ('chat1',1,{**self.payload,'draft':'x'*8_000_000})]:
            with self.assertRaises(ValueError): self.store.save(item_id,'conversation',revision,payload)
        self.assertEqual(self.store.get('chat1')['revision'],1)


if __name__ == '__main__': unittest.main()
