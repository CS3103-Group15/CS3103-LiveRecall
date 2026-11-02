#!/usr/bin/env python3
"""Rebuild the five-page report from measured final results (optional ReportLab)."""
import json
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Flowable

ROOT = Path(__file__).resolve().parents[1]
data = json.loads((ROOT / 'results/final/summary.json').read_text())
checks = json.loads((ROOT / 'results/final/metadata.json').read_text())
for name in ('t1', 't2', 't3', 't4', 't5'):
    assert data['tests'][name]['runs'] >= 3, 'Report requires three runs per public test'
assert data['comparison_t5'], 'Report requires measured before/after data'
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='BodyTextReport', fontName='Helvetica', fontSize=9.5, leading=13, spaceAfter=7))
styles.add(ParagraphStyle(name='SectionReport', fontName='Helvetica-Bold', fontSize=11, leading=14, spaceBefore=7, spaceAfter=6, textColor=colors.HexColor('#16364a')))
styles.add(ParagraphStyle(name='TitleReport', fontName='Helvetica-Bold', fontSize=20, leading=24, spaceAfter=10, textColor=colors.HexColor('#16364a')))
styles.add(ParagraphStyle(name='SmallReport', fontName='Helvetica', fontSize=8, leading=10.5, spaceAfter=6))
styles.add(ParagraphStyle(name='CellReport', fontName='Helvetica', fontSize=8, leading=10))
items = []
def text(s, small=False): items.append(Paragraph(s, styles['SmallReport' if small else 'BodyTextReport']))
def heading(s): items.append(Paragraph(s, styles['SectionReport']))
def page(title, subtitle):
    if items: items.append(PageBreak())
    items.append(Paragraph(title, styles['TitleReport'])); text(subtitle, True)
def table(rows, widths=None):
    cells = [[Paragraph(escape(str(x)), styles['CellReport']) for x in row] for row in rows]
    t = Table(cells, colWidths=widths, repeatRows=1, hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eaf2f6')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),.6,colors.HexColor('#9bb2bf')),('LINEBELOW',(0,1),(-1,-1),.25,colors.HexColor('#d7e0e5')),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
    items.append(t);items.append(Spacer(1,9))
class Architecture(Flowable):
    def __init__(self):
        super().__init__()
        self.width = 510
        self.height = 117
    def draw(self):
        c=self.canv
        def box(x,y,w,h,title,detail):
            c.setFillColor(colors.HexColor('#eef5f8'));c.setStrokeColor(colors.HexColor('#9bb2bf'));c.roundRect(x,y,w,h,5,fill=1,stroke=1)
            c.setFillColor(colors.HexColor('#16364a'));c.setFont('Helvetica-Bold',9);c.drawCentredString(x+w/2,y+h-15,title)
            c.setFont('Helvetica',7.5);c.drawCentredString(x+w/2,y+10,detail)
        def arrow(x1,y1,x2,y2):
            c.setStrokeColor(colors.HexColor('#4a7187'));c.line(x1,y1,x2,y2)
            c.line(x2,y2,x2-4,y2+3);c.line(x2,y2,x2-4,y2-3)
        box(0,47,95,45,'Caption source','segments + revisions')
        box(118,47,125,45,'State + shared history','validate / store finals')
        box(267,47,108,45,'Delivery hub','enqueue; no socket wait')
        arrow(95,69,118,69);arrow(243,69,267,69)
        for y,name in [(76,'Browser A'),(38,'Browser B'),(0,'Browser C')]:
            box(404,y,105,33,name,'own sender + bookmark');arrow(375,69,404,y+16)
items.append(Paragraph('LiveRecall: reliable caption delivery', styles['TitleReport']))
text('CS3103 Assignment 4 | Group 15 | Technical report | Validation: 1 November 2026', True)
heading('1. Architecture and compatibility')
text('LiveRecall distributes a changing caption stream and lets students recover recent finalized context. The mandatory system is the supplied deterministic caption source, our WebSocket server, and browser clients. Performance tests use simulated clients inside the same Ubuntu VM; the browser demonstration is separate.')
items.append(Architecture());items.append(Spacer(1,8))
text('The required entry point is <font face="Courier">python solution_server.py --port 8765</font>. It creates one application and routes the initial SOURCE_HELLO or CLIENT_HELLO to the corresponding session handler. Source updates pass through revision validation and final-history commitment before publication. The delivery hub registers sessions and publishes without waiting for any client socket. Each connection owns its sender task.')
heading('Protocol and revision invariants')
text('CAPTION_UPDATE carries session, segment, revision, source_ts, final and text. Positive segment/revision identifiers increase; acceptance requires a newer revision and rejects stale or duplicate state. Once finalized, a segment cannot be overwritten. The source completes a segment before advancing; no fixed revision count is assumed. Extra source fields are ignored, and SOURCE_DONE is not forwarded as a caption.')
text('Finals enter shared history before the state becomes committed and visible to publication. If capacity cannot preserve the declared retention, the update is not silently accepted and lost. Source processing yields to the event loop after publication so buffered input cannot monopolize scheduling. [1,2]')
heading('Module ownership of behavior')
table([['Module','Responsibility'],['application.py / source_session.py','Connection routing, accepted-update transaction and source lifecycle'],['state.py / history.py','Revision/final protection and bounded ordered durable state'],['delivery_hub.py / client_session.py','Registration, nonblocking publication, client queues and sender policy'],['client/app.js','In-place revisions, local recall, reconnect checkpoint and HISTORY merge']],[190,320])

page('State, recall and recovery','2 / 5 | One shared recent history; independent connection lifecycles')
heading('2. Browser state and local recall')
text('Each segment has one live DOM row. A newer provisional replaces that row; a final changes its style and enters the local finalized map. Older revisions and duplicate finals cannot append a second line. Final history is retained for 70 seconds; the visible live tail is 15 seconds. Recall defaults to 30 seconds, with 15/30/60-second choices using local state without a server round trip. Source timestamps define the age windows.')
text('The browser connects to the hostname serving its page, allowing a Mac browser to use the Ubuntu VM directly. A later recovered final also removes abandoned older provisional rows after a long outage. Browser-state tests cover this case in addition to revision replacement, window selection, checkpoint resume and deduplication.')
heading('Atomic attachment and initial history')
text('CLIENT_HELLO reports the latest finalized segment/revision already held by the client and requests up to 60 seconds of context. Under the application lock, attachment selects only missing recent finals, prepares ordered HISTORY, captures the live-history sequence cursor and registers the session. No network await occurs in that transaction. Publication after registration therefore cannot fall into an attachment gap.')
text('The sender transmits initial HISTORY first, then live work. A slow history transfer blocks only that connection. A browser merges history through the same revision/final guards, so reconnect recovery does not duplicate displayed final state. Recently recovered finals may appear in the live tail; older recovered finals remain available in local recall.')
heading('Two different progress markers')
table([['Marker','Meaning','Lifetime'],['Browser checkpoint','Last final actually accepted by the browser; reported in CLIENT_HELLO','Survives WebSocket reconnect in the same page'],['Server next_final bookmark','Next shared-history sequence to send on this connection','Recreated for each attached session']],[105,250,155])
text('These markers need not differ by exactly one: sequence numbers and segment IDs are distinct, history may be delivered in one initial message, and sending is not proof of application consumption. Reloading a browser page resets its in-memory checkpoint and requests fresh recent context. It does not request the entire lecture.')
heading('Finite recovery contract')
text('Server history is time-bounded to 70 seconds, sufficient for requests up to 60 seconds, with hard limits of 20,000 finals and 32 MiB. A connection whose unsent final cursor expires is closed rather than silently jumping over lost state or accumulating an unbounded backlog. An outage beyond retained context cannot recover an unlimited transcript. [1]')

page('Independent bounded delivery','3 / 5 | Semantic overload handling and RTT-aware feedback')
heading('3. Sender policy and resource bounds')
text('A client queue contains only unsent provisionals. Finals remain in shared history and are read through its bookmark. A healthy sender preserves source order: a segment\'s provisionals precede its final, and a later segment cannot jump ahead of an earlier final. Queue insertion never awaits a socket or full queue.')
table([['Bound / signal','Policy'],['Provisional pending work','At most 256 entries / 1 MiB per connection'],['Feedback pipeline','At most 8 messages; 64 KiB byte threshold checks after the current message (one-message overshoot possible)'],['Send / ping timeout','10 seconds for each awaited operation; close only the affected connection'],['Congestion signals','Queue length/bytes/age, send duration, transport buffer, final lag, and feedback RTT above baseline; severe lag 250 ms; two consecutive mild observations confirm pressure']],[155,355])
text('Under congestion, compaction removes provisionals already superseded by a stored final and keeps the latest queued revision for an active segment. A cadence-aware replacement window applies only to congested provisionals: it is at least 250 ms and at most 1 s. A newer revision restarts the quiet wait, but a 2 s cap prevents perpetual voluntary deferral once the sender can transmit. Network stalls can add further delay. A final removes obsolete work and wakes the sender immediately. Finals are not skipped by compaction.')
heading('Why transport feedback is needed')
text('A successful send may only mean bytes entered network buffers. Once sent, obsolete revisions cannot be retracted. Ping/pong checkpoints keep more pending work in the replaceable application queue. Python slow readers eventually pause transport reads when their receive queue fills, delaying pongs. A pong confirms WebSocket transport progress, not browser display or application acceptance. [3,4]')
heading('High-RTT optimization')
text('Waiting for a pong after every message limits a healthy link to roughly one message per RTT. The revised policy uses the connection\'s best measured RTT and an exponentially smoothed accepted-update interval. The default batch is bounded by ceil(2 x baseline RTT / observed interval), a minimum of one and a maximum of eight. A byte cap independently forces a checkpoint. This avoids assuming particular client roles, source revision counts or hidden workloads.')
text('Fast links retain one-message feedback. On longer-RTT links, the small pipeline reduces artificial stop-and-wait delay while the existing pressure policy still suppresses obsolete provisionals. The ping write itself is also timed out, and cancellation cleans up connection work.')
heading('Recovery trade-off')
text('High/low thresholds and a quiet interval prevent mode flapping. A large feedback delay can retain coalescing for up to 60 seconds. This conservative hold helped final preservation but can delay restoration of full provisional coverage after a temporary bottleneck. Useful finals continue; a future measured recovery controller should test this trade-off explicitly.')

page('Ubuntu experiments and results','4 / 5 | Three independent runs; medians of per-run metrics')
heading('4. Reproducible method')
text('All server, source and simulated clients ran inside the existing VMware Ubuntu 24.04 Mininet lab VM (4 vCPUs, 4 GiB). The main filesystem was extended into already-unused volume-group space; final experiments used the permanent project on disk. The school runner, source, clients and analyser match the supplied starter byte-for-byte. Each run restarts the server. Test parameters, seeds, hashes, raw data, logs, profiles and resource observations are retained in results/final/raw_results.zip.')
text('T1 uses 20 clients for 20 s; T2 uses 100 for 40 s; T3 uses 100 for 60 s with 10% reading at 500 ms/message; T4 uses 100 for 60 s with 20% offline at 15 s for 5 s. T5 uses 100 for 40 s with the supplied 120 ms delay, 30 ms jitter and 3% packet loss on lo. The extra bandwidth experiment applies a separately documented 512 kbit/s TBF cap; it is not a sixth mandatory test.')
rows=[['Test','Final %','Fresh %','Fresh final %','Coverage %','P50 ms','P95 ms','P99 ms']]
for name,r in data['tests'].items():
    m=r['medians']; rows.append([name.upper(),*(f'{m[k]:.2f}' for k in ['final_completeness_pct','fresh_pct','fresh_final_pct','normal_update_coverage_pct','p50_ms','p95_ms','p99_ms'])])
table(rows,[40,57,57,64,63,57,57,57])
text('Caption Age is client receive time minus source_ts. Freshness uses the public 500 ms threshold. Completeness counts unique required finals, while update coverage counts source revisions. The table is the median of each run\'s metric, not percentiles pooled across runs. Per-run completeness remains visible in SUMMARY.md; medians must not hide a weak individual run.')
r=data['tests']['t3']; normal=r['normal_clients'];slow=r['slow_clients']
text(f"T3 isolation: healthy-client P95 was {normal['p95_ms']:.2f} ms with {normal['fresh_pct']:.2f}% freshness; slow-client P95 was {slow['p95_ms']:.2f} ms. Healthy clients retained {normal['messages']:.0f} live revisions per run (all expected updates). T4 recovery P95 median was {data['tests']['t4']['recovery_p95_ms']:.2f} ms. Recovery timing is interpreted alongside completeness, not as proof on its own.")
errors=sum(r['duplicates']+r['stale']+r['connection_errors'] for r in data['tests'].values())
text(f'Observed duplicate/stale/connection-error counts totalled {errors}. Forty-four Python unit tests and five browser-state tests passed. The wrapper samples server RSS; raw resource observations support short-run boundedness, while hard limits and unit tests establish the declared queue/history caps. Network impairment is reset even when a run fails.')
text('Under slow readers or bandwidth pressure, suppressing obsolete provisionals intentionally lowers overall coverage; unconstrained T1/T2 and the healthy population must still retain full updates. An offline final recovered later cannot meet a 500 ms source-age deadline. TCP loss preserves ordered delivery through retransmission but increases head-of-line and tail delay; a fixed experiment cutoff may leave the last final pending. [3]')

page('Optimization evidence and limitations','5 / 5 | Controlled comparison, critical evaluation and future work')
heading('5. Before/after optimization comparison')
text('The earlier sender (fb3e54b, one-message feedback) and revised sender were measured with the same T5 command, VM, persistent filesystem and school programs, three runs each. Only the delivery policy changed in the measured server path. Loss is random and three samples do not establish statistical significance; the results support the engineering trade-off rather than a universal guarantee.')
rows=[['Metric','Before median','After median']]
for key,label,unit in [('final_completeness_pct','Final completeness','%'),('fresh_final_pct','Fresh final ratio','%'),('normal_update_coverage_pct','Revision coverage','%'),('p95_ms','P95 caption age','ms'),('p99_ms','P99 caption age','ms')]:
    row=data['comparison_t5'][key];rows.append([label,f"{row['before']:.2f} {unit}",f"{row['after']:.2f} {unit}"])
table(rows,[240,135,135])
p=data['comparison_t5']['p95_ms'];cov=data['comparison_t5']['normal_update_coverage_pct']
text(f"Bounded RTT-aware batching changed median P95 by {(p['after']/p['before']-1)*100:+.1f}% and revision coverage by {cov['after']-cov['before']:+.2f} percentage points. The policy preserves the normal full-update path; measured changes in coverage/freshness reflect the trade-off under impairment. The new byte/message caps keep the pipeline finite. Completeness results should be read exactly as measured, not inferred from freshness.")
heading('Failures, limits and AI evaluation')
text('Earlier QEMU-based Ubuntu runs generated a tail final after clients had stopped. An instrumented diagnostic found final 22 about 0.26 s after the client cutoff. A longer receive window was diagnostic only, not a substituted public score. The existing VMware VM showed accurate timers and passed the unchanged basic workload. Final comparisons therefore avoid mixing QEMU, Mac and VMware scores.')
text('A brief 130 ms scheduling spike exposed overly eager coalescing in an earlier normal run. Mild send/feedback delays now require two consecutive observations, while 250 ms severe lag acts immediately; regression tests cover both cases. The initial AI-generated per-message ping design improved slow-reader feedback but added unnecessary serial waits on high-RTT links. We changed it to bounded cadence-aware batching and validated both unconstrained revision coverage and impaired-link behavior. Pongs still cannot identify a UI-only stall if the browser continues processing control frames. Already transmitted work cannot be compacted. Memory and retention caps cannot support an unlimited transcript or arbitrarily long disconnection.')
text('The current public suite is not the hidden evaluator: larger populations, faster/burstier revisions, combined impairment, lower bandwidth and post-overload recovery can expose other limits. The 99% hidden completeness gate is not a promise of a score. The mandatory two-browser video and individual viva remain human deliverables; team contribution details are deferred for team agreement. No optional ASR result is claimed.')
heading('Future direction and references')
text('Future work should measure bounded adaptive recovery after temporary overload, application-level receipt feedback for participating browsers, fair scheduling under mixed bottlenecks and deployment capacity. A longer-term classroom system would add session lifecycle, privacy/authentication and optional ASR through the same caption protocol, without changing the mandatory lightweight evaluation path.')
text('[1] NUS CS3103, Assignment 4: LiveRecall, updated 17 October 2026. [2] Supplied public test/protocol guides and unchanged harness; exact configurations and raw evidence in results/final/. [3] RFC 6455, sections 5.5.2-5.5.3: www.rfc-editor.org/rfc/rfc6455.html. [4] websockets documentation, Memory and buffers: websockets.readthedocs.io/en/stable/topics/memory.html. AI/tool use is declared in AI_USAGE.md.', True)

def footer(canvas, doc):
    canvas.setStrokeColor(colors.HexColor('#d7e0e5')); canvas.line(42,35,A4[0]-42,35)
    canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#526b78'))
    canvas.drawString(42,23,'CS3103 Group 15 | LiveRecall | 1 November 2026')
    canvas.drawRightString(A4[0]-42,23,str(doc.page))

doc=SimpleDocTemplate(str(ROOT/'report.pdf'),pagesize=A4,rightMargin=42,leftMargin=42,topMargin=38,bottomMargin=47,title='LiveRecall: reliable caption delivery',author='CS3103 Group 15')
doc.build(items,onFirstPage=footer,onLaterPages=footer)
print(ROOT/'report.pdf')
