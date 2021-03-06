
#################################################
### THIS FILE WAS AUTOGENERATED! DO NOT EDIT! ###
#################################################
# file to edit: dev_nb/04_callbacks.ipynb

from exp.nb_03 import *

class DataBunch():
    def __init__(self, train_dl, valid_dl):
        self.train_dl,self.valid_dl = train_dl,valid_dl
        self.c = self.train_ds.y.max().item()+1

    @property
    def train_ds(self): return self.train_dl.dataset

    @property
    def valid_ds(self): return self.valid_dl.dataset

def get_model(data, lr=0.5, nh=50):
    m = data.train_ds.x.shape[1]
    model = nn.Sequential(nn.Linear(m,nh), nn.ReLU(), nn.Linear(nh,data.c))
    return model, optim.SGD(model.parameters(), lr=lr)

class Learner():
    def __init__(self, model, opt, loss_func, data):
        self.model,self.opt,self.loss_func,self.data = model,opt,loss_func,data

class Callback(): _order=0

class TrainEvalCallback(Callback):
    def begin_fit(self, run):
        run.n_epochs=0.
        run.n_iter=0

    def after_batch(self, run):
        if run.in_train:
            run.n_epochs += 1./run.iters
            run.n_iter   += 1

    def begin_epoch(self, run):
        run.n_epochs=run.epoch
        run.model.train()
        run.in_train=True

    def begin_validate(self, run):
        run.model.eval()
        run.in_train=False

def listify(o):
    if o is None: return []
    if isinstance(o, list): return o
    if isinstance(o, tuple): return list(o)
    return [o]

class Runner():
    def __init__(self, cbs=None):
        self.stop,self.cbs = False,[TrainEvalCallback()]+listify(cbs)

    @property
    def opt(self):       return self.learn.opt
    @property
    def model(self):     return self.learn.model
    @property
    def loss_func(self): return self.learn.loss_func
    @property
    def data(self):      return self.learn.data

    def one_batch(self, xb, yb):
        self.xb,self.yb = xb,yb
        if self('begin_batch'): return
        self.pred = self.model(self.xb)
        if self('after_pred'): return
        self.loss = self.loss_func(self.pred, self.yb)
        if self('after_loss') or not self.in_train: return
        self.loss.backward()
        if self('after_backward'): return
        self.opt.step()
        if self('after_step'): return
        self.opt.zero_grad()

    def all_batches(self, dl):
        self.iters = len(dl)
        for xb,yb in dl:
            if self.stop: break
            self.one_batch(xb, yb)
            self('after_batch')
        self.stop=False

    def fit(self, epochs, learn):
        self.epochs,self.learn = epochs,learn

        try:
            if self('begin_fit'): return
            for epoch in range(epochs):
                self.epoch = epoch
                if not self('begin_epoch'): self.all_batches(self.data.train_dl)

                with torch.no_grad():
                    if not self('begin_validate'): self.all_batches(self.data.valid_dl)
                if self('after_epoch'): break

        finally:
            self('after_fit')
            self.learn = None

    def __call__(self, cb_name):
        for cb in sorted(self.cbs, key=lambda x: x._order):
            f = getattr(cb, cb_name, None)
            if f and f(self): return True
        return False

class AvgStats():
    def __init__(self, metrics, in_train): self.metrics,self.in_train = listify(metrics),in_train

    def reset(self):
        self.tot_loss,self.count = 0.,0
        self.tot_mets = [0.] * len(self.metrics)

    @property
    def all_stats(self): return [self.tot_loss.item()] + self.tot_mets

    def __repr__(self):
        if not self.count: return ""
        return f"{'train' if self.in_train else 'valid'}: {[o/self.count for o in self.all_stats]}"

    def accumulate(self, run):
        bn = run.xb.shape[0]
        self.tot_loss += run.loss * bn
        self.count += bn
        for i,m in enumerate(self.metrics):
            self.tot_mets[i] += m(run.pred, run.yb) * bn

class AvgStatsCallback(Callback):
    def __init__(self, metrics):
        self.train_stats,self.valid_stats = AvgStats(metrics,True),AvgStats(metrics,False)

    def stats(self, run): return self.train_stats if run.in_train else self.valid_stats

    def begin_epoch(self, run):
        self.train_stats.reset()
        self.valid_stats.reset()

    def after_loss(self, run):
        with torch.no_grad(): self.stats(run).accumulate(run)

    def after_epoch(self, run):
        print(self.train_stats)
        print(self.valid_stats)