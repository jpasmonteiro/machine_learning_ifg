import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import json, numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score,
                             roc_auc_score, confusion_matrix, roc_curve)
from config.settings import PROCESSED_DIR, EVID_DIR, SEED
from src.ml.features import split_and_scale
from src.ml.knn_scratch import KNNScratch
K_NEIGHBORS = 15
def _m(yt, yp, ys):
    return {"accuracy": round(accuracy_score(yt, yp),4), "precision": round(precision_score(yt,yp,zero_division=0),4),
            "recall": round(recall_score(yt,yp,zero_division=0),4), "f1": round(f1_score(yt,yp,zero_division=0),4),
            "roc_auc": round(roc_auc_score(yt, ys),4)}
def _mm(v):
    v=np.asarray(v,float); lo,hi=v.min(),v.max(); return (v-lo)/(hi-lo) if hi>lo else np.zeros_like(v)
def run():
    df = pd.read_csv(PROCESSED_DIR/"ml_features.csv")
    X_tr,X_te,y_tr,y_te,id_te,cols = split_and_scale(df, seed=SEED)
    Xtr,Xte = X_tr.values.astype(float), X_te.values.astype(float); r={}
    maj=int(pd.Series(y_tr).mode()[0]); yb=np.full_like(y_te,maj)
    r["baseline_majoritaria"]=_m(y_te,yb,np.full(len(y_te),maj,dtype=float))
    df_te=df.set_index("ticket_id").loc[id_te]
    yr=df_te["priority"].isin(["Alta","Crítica"]).astype(int).values
    r["baseline_regra_prioridade"]=_m(y_te,yr,yr.astype(float))
    knn_hc=KNNScratch(k=K_NEIGHBORS).fit(Xtr,y_tr); p_hc=knn_hc.predict_proba(Xte)[:,1]; y_hc=(p_hc>=0.5).astype(int)
    r["knn_hardcode"]=_m(y_te,y_hc,p_hc)
    knn=KNeighborsClassifier(n_neighbors=K_NEIGHBORS).fit(Xtr,y_tr); p_sk=knn.predict_proba(Xte)[:,1]; y_sk=knn.predict(Xte)
    r["knn_sklearn"]=_m(y_te,y_sk,p_sk)
    svm=SVC(kernel="rbf",C=1.0,random_state=SEED).fit(Xtr,y_tr); s_svm=svm.decision_function(Xte); y_svm=svm.predict(Xte)
    r["svm"]=_m(y_te,y_svm,s_svm)
    mlp=MLPClassifier(hidden_layer_sizes=(64,32),max_iter=500,random_state=SEED).fit(Xtr,y_tr); p_mlp=mlp.predict_proba(Xte)[:,1]; y_mlp=mlp.predict(Xte)
    r["mlp"]=_m(y_te,y_mlp,p_mlp)
    comp={"concordancia_hardcode_vs_sklearn":round(float((y_hc==y_sk).mean()),4),
          "diff_f1":round(r["knn_sklearn"]["f1"]-r["knn_hardcode"]["f1"],4),
          "diff_roc_auc":round(r["knn_sklearn"]["roc_auc"]-r["knn_hardcode"]["roc_auc"],4),"k":K_NEIGHBORS}
    cand={k:r[k] for k in ["knn_hardcode","knn_sklearn","svm","mlp"]}; best=max(cand,key=lambda k:cand[k]["f1"])
    smap={"knn_hardcode":p_hc,"knn_sklearn":p_sk,"svm":_mm(s_svm),"mlp":p_mlp}
    pmap={"knn_hardcode":y_hc,"knn_sklearn":y_sk,"svm":y_svm,"mlp":y_mlp}
    pd.DataFrame({"ticket_id":id_te,"y_true":y_te,"proba_breach":np.round(smap[best],4),"y_pred":pmap[best],"modelo":best}).to_csv(PROCESSED_DIR/"predictions.csv",index=False)
    cm=confusion_matrix(y_te,pmap[best])
    fig,ax=plt.subplots(figsize=(4.2,3.6)); ax.imshow(cm,cmap="Blues")
    ax.set_xticks([0,1]);ax.set_yticks([0,1]);ax.set_xticklabels(["Não viola","Viola"]);ax.set_yticklabels(["Não viola","Viola"])
    ax.set_xlabel("Previsto");ax.set_ylabel("Real");ax.set_title(f"Matriz de Confusão ({best})")
    for (rr,cc),v in np.ndenumerate(cm): ax.text(cc,rr,str(v),ha="center",va="center",color="white" if v>cm.max()/2 else "black",fontsize=12)
    fig.tight_layout();fig.savefig(EVID_DIR/"matriz_confusao.png",dpi=130);plt.close(fig)
    fig,ax=plt.subplots(figsize=(4.6,3.8))
    for nm,sc in [("KNN (na mão)",p_hc),("KNN (sklearn)",p_sk),("SVM",_mm(s_svm)),("MLP",p_mlp)]:
        fpr,tpr,_=roc_curve(y_te,sc); ax.plot(fpr,tpr,label=f"{nm} (AUC={roc_auc_score(y_te,sc):.3f})")
    ax.plot([0,1],[0,1],"k--",alpha=.4);ax.set_xlabel("Falso Positivo");ax.set_ylabel("Verdadeiro Positivo")
    ax.set_title("Curva ROC");ax.legend(loc="lower right",fontsize=8);fig.tight_layout();fig.savefig(EVID_DIR/"curva_roc.png",dpi=130);plt.close(fig)
    out={"tarefa":"classificacao binaria (sla_breach)","algoritmos":"KNN (hard-code + sklearn), SVM, MLP",
         "n_treino":int(len(y_tr)),"n_teste":int(len(y_te)),"n_atributos":len(cols),
         "prevalencia_alvo_teste":round(float(y_te.mean()),4),"metricas":r,
         "comparacao_hardcode_vs_sklearn":comp,"modelo_producao":best}
    json.dump(out,open(EVID_DIR/"metrics.json","w",encoding="utf-8"),ensure_ascii=False,indent=2)
    print(pd.DataFrame(r).T.to_string()); print("comp:",comp,"| producao:",best)
    return out
if __name__=="__main__": run()
