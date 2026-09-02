"""HTTP entry point for command events."""
import logging
from functools import wraps

from flask import Flask, jsonify, request, session, redirect, url_for
from werkzeug.exceptions import BadRequest

from config import Config
from handlers.capture import handle_capture
from ledger import query_expenses, statistics, update_expense, delete_expense


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    app.logger.setLevel(logging.INFO)
    app.secret_key = app.config.get("SECRET_KEY") or "change-this"

    def dashboard_auth(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            expected_user = app.config.get("DASHBOARD_USERNAME")
            expected_password = app.config.get("DASHBOARD_PASSWORD")
            if session.get("dashboard_user") == expected_user:
                return fn(*args, **kwargs)
            return redirect(url_for("login", next=request.path))
            return fn(*args, **kwargs)
        return wrapped

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            if request.form.get('username') == app.config.get('DASHBOARD_USERNAME') and request.form.get('password') == app.config.get('DASHBOARD_PASSWORD'):
                session['dashboard_user'] = request.form.get('username')
                return redirect(request.form.get('next') or url_for('dashboard'))
            return '로그인 정보가 올바르지 않습니다', 401
        return '''<!doctype html><meta name=viewport content='width=device-width'><title>가계부 로그인</title><style>body{font-family:sans-serif;max-width:360px;margin:60px auto;padding:20px}input,button{box-sizing:border-box;width:100%;padding:13px;margin:7px 0;font-size:16px}button{background:#2563eb;color:white;border:0;border-radius:6px}</style><h2>가족 가계부 로그인</h2><form method=post><input name=username placeholder='아이디' required><input name=password type=password placeholder='비밀번호' required><button>로그인</button></form>'''

    @app.get("/")
    @dashboard_auth
    def dashboard():
        return """<!doctype html><html lang=ko><head><meta name=viewport content="width=device-width,initial-scale=1"><title>Household Ledger</title><script src="https://cdn.jsdelivr.net/npm/chart.js"></script><style>
*{box-sizing:border-box}body{margin:0;background:#f5f7fb;color:#172033;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}header{background:linear-gradient(135deg,#4338ca,#7c3aed);color:white;padding:28px 18px 70px}header,.wrap{max-width:1100px;margin:auto}.top{display:flex;justify-content:space-between;align-items:center}.brand{font-size:22px;font-weight:800}.sub{opacity:.8;font-size:13px;margin-top:5px}.wrap{margin:-45px auto 40px;padding:0 16px}.toolbar{background:white;border-radius:16px;padding:14px;box-shadow:0 8px 25px #1e1b4b18;display:flex;gap:10px;align-items:center;flex-wrap:wrap}.toolbar label{font-size:13px;color:#64748b}.toolbar input,.toolbar select{border:1px solid #dbe2ef;border-radius:9px;padding:9px;font-size:14px;background:#fff}.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:18px 0}.card,.panel{background:white;border-radius:16px;padding:18px;box-shadow:0 3px 14px #1e293b0b}.label{font-size:13px;color:#64748b}.value{font-size:27px;font-weight:800;margin-top:8px}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.panel h3{margin:0 0 8px;font-size:14px;color:#475569}.chartbox{height:145px;position:relative}.tablewrap{overflow:auto}table{width:100%;border-collapse:collapse;white-space:nowrap}th,td{text-align:left;padding:12px 8px;border-bottom:1px solid #eef1f6;font-size:14px}th{color:#64748b;font-weight:600}.money{font-weight:700;text-align:right}.pill{display:inline-block;border-radius:99px;background:#eef2ff;color:#4338ca;padding:4px 9px;font-size:12px}@media(max-width:700px){.grid{grid-template-columns:1fr 1fr}.chartbox{height:120px}header{padding-bottom:62px}.cards{grid-template-columns:1fr 1fr}.cards .card:first-child{grid-column:span 2}.grid{grid-template-columns:1fr}.value{font-size:22px}.toolbar>*{flex:1}}
</style></head><body><header><div class=top><div><div class=brand>Household Ledger</div><div class=sub>우리 가족의 지출을 한눈에</div></div><div>⌂</div></div></header><main class=wrap><div class=toolbar><label>조회 월</label><input id=month type=month><select id=user><option value="">모든 사용자</option></select><select id=category><option value="">모든 카테고리</option></select><button onclick=load() style="border:0;border-radius:9px;padding:10px 16px;background:#4338ca;color:white">조회</button></div><section class=cards><div class=card><div class=label>선택 기간 지출</div><div id=total class=value>₩0</div></div><div class=card><div class=label>거래 건수</div><div id=count class=value>0건</div></div><div class=card><div class=label>가장 큰 지출</div><div id=largest class=value>₩0</div></div></section><section class=grid><div class=panel><h3>월별 지출 추이</h3><div class=chartbox><canvas id=monthly></canvas></div></div><div class=panel><h3>카테고리별 비율</h3><div class=chartbox><canvas id=cat></canvas></div></div><div class=panel><h3>사용자별 지출</h3><div class=chartbox><canvas id=users></canvas></div></div><div class=panel><h3>카테고리별 합계</h3><div id=catlist></div></div></section><section class="panel" style="margin-top:14px"><h3>최근 지출</h3><div class=tablewrap><table><thead><tr><th>날짜</th><th>사용자</th><th>내용</th><th>카테고리</th><th>금액</th><th></th></tr></thead><tbody id=rows></tbody></table></div></section></main><script>
(function(){
 var month=document.getElementById('month');
 month.value=new Date().toISOString().slice(0,7);
 function won(n){return '₩'+Number(n||0).toLocaleString('ko-KR');}
 function load(){
  var m=month.value;
  Promise.all([fetch('/api/statistics?month='+m),fetch('/api/expenses?month='+m)]).then(function(rs){return Promise.all([rs[0].json(),rs[1].json()]);}).then(function(data){
   var st=data[0], ex=data[1];
   document.getElementById('total').textContent=won(ex.reduce(function(a,x){return a+Number(x.amount||0);},0));
   document.getElementById('count').textContent=ex.length+'건';
   document.getElementById('largest').textContent=won(Math.max.apply(null,[0].concat(ex.map(function(x){return Number(x.amount||0);})))) ;var cats={};var users={};ex.forEach(function(x){var c=x.category||'기타',u=x.name||'미지정';cats[c]=(cats[c]||0)+Number(x.amount||0);users[u]=(users[u]||0)+Number(x.amount||0);});
   document.getElementById('catlist').innerHTML=Object.keys(cats).map(function(k){return '<p><span class=pill>'+k+'</span><b style="float:right">'+won(cats[k])+'</b></p>';}).join('')||'<p>데이터가 없습니다</p>';
   if(typeof Chart!=='undefined'){if(window._cat)window._cat.destroy();window._cat=new Chart(document.getElementById('cat'),{type:'doughnut',data:{labels:Object.keys(cats),datasets:[{data:Object.values(cats),backgroundColor:['#4f46e5','#06b6d4','#f59e0b','#ef4444','#10b981','#8b5cf6']}]},options:{responsive:true,maintainAspectRatio:false}});if(window._users)window._users.destroy();window._users=new Chart(document.getElementById('users'),{type:'bar',data:{labels:Object.keys(users),datasets:[{data:Object.values(users),backgroundColor:'#4f46e5'}]},options:{responsive:true,maintainAspectRatio:false}});if(window._monthly)window._monthly.destroy();window._monthly=new Chart(document.getElementById('monthly'),{type:'bar',data:{labels:(st.monthly||[]).map(function(x){return x.label;}),datasets:[{data:(st.monthly||[]).map(function(x){return x.total;}),backgroundColor:'#06b6d4'}]},options:{responsive:true,maintainAspectRatio:false}});}
   document.getElementById('rows').innerHTML=ex.map(function(x){return '<tr><td>'+x.spent_at+'</td><td>'+((x.name)||'-')+'</td><td><input id="c'+x.id+'" value="'+((x.merchant)||x.description)+'" style="width:130px;padding:7px" disabled></td><td><select id="g'+x.id+'" style="padding:7px" disabled><option>식비</option><option>여가</option><option>통신/구독</option><option>경조사</option><option>쇼핑</option><option>주거/생활</option></select></td><td><input id="a'+x.id+'" type=text inputmode=numeric value="'+x.amount+'" style="width:100px;padding:7px" disabled></td><td><button onclick="window.editExpense('+x.id+')">수정</button> <button onclick="window.deleteExpense('+x.id+')">삭제</button></td></tr>';}).join('');ex.forEach(function(x){var q=document.getElementById('g'+x.id);if(q)q.value=x.category||'식비';});
  }).catch(function(e){console.error(e);});
 }
 window.deleteExpense=function(id){if(confirm('이 지출을 삭제할까요?'))fetch('/api/expenses/'+id,{method:'DELETE'}).then(load);};
 window.editExpense=function(id){var c=document.getElementById('c'+id),a=document.getElementById('a'+id),g=document.getElementById('g'+id),b=event&&event.target;if(c){c.disabled=false;a.disabled=false;g.disabled=false;if(b){b.textContent='저장';b.onclick=function(){window.saveExpense(id);};}}};
 window.saveExpense=function(id){var content=document.getElementById('c'+id).value,amount=Number(document.getElementById('a'+id).value),category=document.getElementById('g'+id).value;if(!content||!amount)return;fetch('/api/expenses/'+id,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({content:content,amount:amount,category:category})}).then(load);};
 window.load=load; load();
})();
</script></body></html>"""

    @app.get("/api/expenses")
    @dashboard_auth
    def expenses_api():
        return jsonify(query_expenses(request.args.get("month")))

    @app.get("/api/statistics")
    @dashboard_auth
    def statistics_api():
        return jsonify(statistics(request.args.get("month")))

    @app.put("/api/expenses/<int:expense_id>")
    @dashboard_auth
    def update_api(expense_id):
        data=request.get_json(silent=True) or {}
        if not data.get("content") or data.get("category") not in {"식비","여가","통신/구독","경조사","쇼핑","주거/생활"} or not isinstance(data.get("amount"), int): return jsonify(error="invalid input"),400
        update_expense(expense_id,data["content"],data["category"],data["amount"]); return jsonify(result="ok")

    @app.delete("/api/expenses/<int:expense_id>")
    @dashboard_auth
    def delete_api(expense_id):
        delete_expense(expense_id); return jsonify(result="ok")

    @app.post("/event")
    def event():
        expected_token = app.config["API_BEARER_TOKEN"]
        if expected_token:
            authorization = request.headers.get("Authorization", "")
            if authorization != f"Bearer {expected_token}":
                return jsonify(error="Unauthorized"), 401

        if not request.is_json:
            return jsonify(error="Request body must be JSON"), 400

        try:
            payload = request.get_json()
        except BadRequest:
            return jsonify(error="Invalid JSON"), 400

        if not isinstance(payload, dict):
            return jsonify(error="JSON object is required"), 400

        command = payload.get("command")
        message = payload.get("message")
        if not isinstance(command, str) or not command.strip():
            return jsonify(error="Missing required field: command"), 400
        if not isinstance(message, str) or not message.strip():
            return jsonify(error="Missing required field: message"), 400

        handlers = {"capture": handle_capture}
        handler = handlers.get(command)
        if handler is None:
            return jsonify(error=f"Unsupported command: {command}"), 400

        handler(message)
        return jsonify(result="ok"), 200

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
