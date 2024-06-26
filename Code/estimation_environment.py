import numpy as np
from gymnasium import Env
from gymnasium.spaces import Discrete, Box, Tuple, MultiDiscrete, Dict
import matplotlib.pyplot as plt

def get_initial_p(b0, sig, grid):
    p = np.exp(-(b0-grid)**2/sig/sig/2) + np.exp(-( b0 + grid)**2/sig/sig/2)
    if np.sum(p)==0:
        p = np.zeros(len(grid))
        p[np.argmin(np.abs(b0-grid))] = 1
    return p/np.sum(p)

def update_p(d, phi, p0):
    q = 2*d-1
    p = p0*(1+q*np.cos(phi))/2.
    if np.sum(p)==0:
        return p0
    return p/np.sum(p)

min_std = 0.01
def get_std(probs, grid):
    if 0 > np.sum(probs*grid**2)-np.sum(probs*grid)**2:
        return min_std 
    else:
        return np.sqrt(np.sum(probs*grid**2)-np.sum(probs*grid)**2)

def estimate(freq_drift, grid, pdf_weights, c = 4,  om0=0, t = None, rng_shot = None):
    omega = freq_drift+om0
    if t == None:
        sig = get_std(pdf_weights, grid)
        t = 1/c/sig
    x = rng_shot.binomial(1, 1/2+1/2*np.cos(2*np.pi*omega*t))
    pdf_weights = update_p(x, 2*np.pi*(grid+om0)*t, pdf_weights)  #TODO
    return pdf_weights
            
def get_estimate(probs, grid):
    return np.sum(probs*grid)
    ind = np.argmax(probs)
    return grid[ind]

def get_initial_p(b0, sig, grid):
    if sig==0:
        sig = self.min_std
        p = np.exp(-(b0-grid)**2/sig/sig/2)
    else:
        p = np.exp(-(b0-grid)**2/sig/sig/2)
    return p/np.sum(p)

def next_B(b0, dt, sig,tc, rng):
    return b0*np.exp(-dt/tc) + sig*np.sqrt(1-np.exp(-2*dt/tc))*rng.normal()

def difuse_pdf(pdf, dt, sig, tc, grid):
    std = np.sqrt(sig**2*(1-np.exp(-2*dt/tc)))
    pdf_t = np.tile(pdf, (len(grid),1))
    grid_t = np.tile(grid, (len(pdf),1))
    grid_t2 = grid_t.T
    pdf = np.sum(pdf_t*np.exp(-(grid_t2-grid_t*np.exp(-dt/tc))**2/(2*std**2)), axis=1)
    return pdf/np.sum(pdf)



class Telegraph_Noise():
    def __init__(self, sigma, gamma, x0=None):
        self.gamma = gamma
        self.sigma = sigma
        if x0 is None:
            self.x = self.sigma*(2*np.random.randint(0, 1)-1)


    def update(self, dt):
        # update telegraph noise
        switch_probability = 1/2 + 1/2*np.exp(-2*self.gamma*dt) 
        if np.random.rand() < switch_probability:
            self.x = -self.x    
        return self.x


class OU_noise():
    def __init__(self, sigma, tc, x0=None):
        self.tc = tc
        self.sigma = sigma
        self.x0 = x0
        if x0 is None:
            self.x = np.abs(np.random.normal(0,sigma))
        else:
            self.x = x0
  
        
    def update(self, dt):
        self.x = self.x*np.exp(-dt/self.tc) + np.sqrt(1-np.exp(-2*dt/self.tc))*np.random.normal(0,self.sigma)
        return self.x

    def reset(self):
        if self.x0 is None:
            self.x = np.abs(np.random.normal(0,self.sigma))
        else:
            self.x = self.x0

class Over_f_noise():
    def __init__(self, n_telegraphs, S1 ,sigma_couplings, ommax, ommin, x0=None):
        self.n_telegraphs = n_telegraphs
        self.S1 = S1
        self.sigma_couplings = sigma_couplings
        self.ommax = ommax
        self.ommin = ommin
        self.spawn_telegraphs(n_telegraphs, sigma_couplings, ommax, ommin, S1)
        if x0 is None:
            self.x = np.sum([telegraph.x for telegraph in self.telegraphs])
        else:
            self.x = x0
        

    def spawn_telegraphs(self, n_telegraphs, sigma_couplings, ommax, ommin, S1):
        uni = np.random.uniform(0,1,size = n_telegraphs)
        gammas = self.ommax*np.exp(-np.log(self.ommax/self.ommin)*uni)
        sigmas = S1*np.random.normal(1,sigma_couplings, size=n_telegraphs)/np.sqrt(n_telegraphs)
        self.telegraphs = []
        for n, gamma in enumerate(gammas):
            self.telegraphs.append(Telegraph_Noise
                                   (sigmas[n], gamma))
        
    def update(self, dt):
        for telegraph in self.telegraphs:
            self.x += telegraph.update(dt)
        return self.x
        

class EstimationEnv(Env):
    def __init__(self, length, tc, om0, sigma, initial_std, c=4, seed_field=None, seed_shot = None):
        # Actions we can take, down, stay, up
        self.seed_shot = seed_shot
        self.seed_field = seed_field
        self.rng_shot = np.random.default_rng(seed_shot)
        self.rng_field = np.random.default_rng(seed_field)
        self.estimaiton_length0 = length
        self.estimation_length = length
        self.sigma = sigma
        self.tc = tc
        self.initial_std = initial_std
        self.c_used = c

        self.action_space = Discrete(3)
        self.observation_space = Box(low = 0, high = 1, shape = (101,),dtype=np.float32) #Implement observation space!
        self.freq_grid = np.linspace(0.1,100,101) 

    


        initial_error = self.rng_field.normal(0, initial_std)
        #initial_error = 0
        self.weigths = get_initial_p(np.abs(om0)+initial_error, initial_std, self.freq_grid)
        self.state = self.weigths

    def step(self, action):
        # Apply action
        # 0 - not estimate
        # 1 - estimate 
        # 2 - nothing

        reward = 0
        b = None
        
        
        mu = self.state[0]
        std = self.state[1]
        
 

        if action == 0:
            if mu==0:
                b = 1
            else:
                t = 1/mu/2 # change np.pi in numerator to have different angle    
                b = self.rng_shot.binomial(1, 1/2+1/2*np.cos(2*np.pi*self.om*t))
            if b==0:
                reward = 1
            else:
                reward = -1

            #self.weigths = update_p(b, 2*np.pi*self.freq_grid*t, self.weigths)
        elif action == 1:
            self.weigths = estimate(self.om, self.freq_grid, self.weigths,  c=self.c_used,
                                    om0 = 0, rng_shot = self.rng_shot,)
        else:
            if mu>0:
                self.weigths = estimate(self.om, self.freq_grid, self.weigths, 
                                    om0 = 0, rng_shot = self.rng_shot, t=1/mu/2)

        #diffuse
 
        self.weigths = difuse_pdf(self.weigths, dt = 1, sig = self.sigma, tc = self.tc, grid = self.freq_grid)
        
        #update knowladge
        
        mu = get_estimate(self.weigths, self.freq_grid)  #get_estimate of field
        std = get_std(self.weigths, self.freq_grid)                 #get_std of field
        self.state = self.weigths
        
        '''
        self.state[0] = mu
        self.state[1] = std
        '''
        #self.state[2] += 1
        #update frequency
        self.om = next_B(self.om, dt = 1, sig = self.sigma, tc = self.tc, rng = self.rng_field)

        self.estimation_length -= 1
        # Check if estimation is done
        if self.estimation_length <= 0: 
            done = True
        else:
            done = False
        
 
        # Set placeholder for info
        truncated = False #?
        info = {"om":self.om }

        # Return step information
        return  np.array(self.state).astype(np.float32), reward, done, truncated, info

    def render(self):
        # Implement viz
        pass
    
    def reset(self,seed=None, options=None):
        self.estimation_length =  self.estimaiton_length0 

        initial_error = self.rng_field.normal(0, self.initial_std)
        #initial_error = 0
        self.weigths = get_initial_p(np.abs(self.om)+initial_error, self.initial_std, self.freq_grid)

        mu = get_estimate(self.weigths, self.freq_grid) 
        std = get_std(self.weigths, self.freq_grid)
        self.state = self.weigths

        info = {"om":self.om}
        return np.array(self.state).astype(np.float32), info


class NoCheck(EstimationEnv):
    def __init__(self, length, tc, om0, sigma, initial_std, c=4, seed_field=None, seed_shot = None):
        super().__init__(length, tc, om0, sigma, initial_std, c, seed_field, seed_shot)    
        self.action_space = Discrete(2)



class FlexibleEstimationTime(EstimationEnv):
    def __init__(self, length, tc, om0, sigma, initial_std, c=4, 
                 seed_field=None, seed_shot = None, penalty = -1, max_time = 100, over_f = True,
                 time_step = 1):
        self.penalty = penalty
        self.over_f = over_f
        self.om0 = om0
        self.time_step = time_step
        if over_f:
            self.noise = Over_f_noise(n_telegraphs=10, S1= 1, sigma_couplings=0.25, ommax=10, ommin = 1/length, x0=om0)

        else:
            self.noise = OU_noise(sigma = sigma, tc =tc, x0 = om0)
        self.om = self.noise.x
        super().__init__(length, tc, self.om, sigma, initial_std, c, seed_field, seed_shot)    
        self.action_space = MultiDiscrete(np.array([2,int(max_time/time_step)]))
     

    def step(self, action):
        # Apply action
        # 0 - not estimate
        # 1 - estimate 
        # 2 - nothing

        reward = 0
        b = None
        #plt.figure()
        #plt.plot(self.freq_grid, self.weigths)

        
        mu = get_estimate(self.weigths, self.freq_grid)
        std = get_std(self.weigths, self.freq_grid)
 

        if action[0] == 0:
            if mu==0:
                b = 1
            else:
                t = 1/mu/2 # change np.pi in numerator to have different angle    
                b = self.rng_shot.binomial(1, 1/2+1/2*np.cos(2*np.pi*(self.om)*t))
            if b==0:
                reward = 1
            else:
                reward = self.penalty

            #self.weigths = update_p(b, 2*np.pi*self.freq_grid*t, self.weigths)
        else:
            #self.weigths = estimate(self.freq_drift, self.freq_grid, self.weigths,  c=self.c_used,
            #                        om0 = self.om0, rng_shot = self.rng_shot,t = action[1]/mu/4)
            self.weigths = estimate(self.om, self.freq_grid, self.weigths,  c=self.c_used,
                                    om0 = 0, rng_shot = self.rng_shot,t = action[1]*self.time_step*1e-3)
        plot_weights = False
        if plot_weights:
            plt.figure()
            plt.plot(self.freq_grid, self.weigths)
        #diffuse
            plt.ylim(0,np.max(self.weigths))
        self.weigths = difuse_pdf(self.weigths, dt = 1, sig = self.sigma, tc = self.tc, grid = self.freq_grid)
        #update knowladge
        
        mu = get_estimate(self.weigths, self.freq_grid)     #get_estimate of field
        std = get_std(self.weigths, self.freq_grid)                 #get_std of field
        self.state = self.weigths
        if plot_weights:
            plt.plot(self.freq_grid, self.weigths, "r--")
            plt.vlines(np.abs(self.om),0,1,"k")

            plt.vlines(mu,0,1,"green")

        #self.state[2] += 1
        #update frequency
        self.noise.update(1)
        if self.over_f:
            self.om = self.noise.x
        else:
            self.om = next_B(self.om, dt = 1, sig = self.sigma, tc = self.tc, rng = self.rng_field)

        self.estimation_length -= 1
        # Check if estimation is done
        if self.estimation_length <= 0: 
            done = True
        else:
            done = False
        
 
        # Set placeholder for info
        truncated = False #?
        info = {"om":self.om}

        # Return step information
        return  np.array(self.state).astype(np.float32), reward, done, truncated, info

    def reset(self,seed=None, options=None):

        self.noise.reset()
        self.om = self.noise.x
        state, info = super().reset()

        
        return state, info

class ConstantFlexibleEstimationTime(EstimationEnv):
    def __init__(self, length, tc, om0, sigma, initial_std,
                 seed_field=None, seed_shot = None,time_grid = 20):
        super().__init__(length, tc, om0, sigma, initial_std, c, seed_field, seed_shot)    
        self.action_space = MultiDiscrete(np.array([max_time]))
        
    def step(self, action):
        # Apply action
        # 0 - not estimate
        # 1 - estimate 
        # 2 - nothing

        reward = 0
        b = None

        
        mu = self.state[0]
        std = self.state[1]
 

        self.weigths = estimate(self.om, self.freq_grid, self.weigths,  c=self.c_used,
                                om0 = 0, rng_shot = self.rng_shot,t = action*1e-3)

        #diffuse
        self.weigths = difuse_pdf(self.weigths, dt = 1, sig = self.sigma, tc = self.tc, grid = self.freq_grid)
        #update knowladge
        mu = get_estimate(self.weigths, self.freq_grid)     #get_estimate of field
        std = get_std(self.weigths, self.freq_grid)                 #get_std of field
        self.state[0] = mu
        self.state[1] = std
        #self.state[2] += 1
        #update frequency
        self.noise.update(1)
        if self.over_f:
            self.om = self.noise.x
        else:
            self.om = next_B(self.om, dt = 1, sig = self.sigma, tc = self.tc, rng = self.rng_field)

        self.estimation_length -= 1
        # Check if estimation is done
        if self.estimation_length <= 0: 
            done = True
        else:
            done = False
        
 
        # Set placeholder for info
        truncated = False #?
        info = {"om":self.om}

        # Return step information
        return  np.array(self.state).astype(np.float32), reward, done, truncated, info




def import_data(results):
    rewards = results.rewards
    actions = results.actions
    oms = results.oms
    mus = results.mus
    std = results.stds
    return rewards, actions, oms, mus, std

def get_outcome(rewards, actions):
    outcome = rewards + actions*2
    outcome[outcome<0] = 0
    return outcome


def analyse_few_games(results, string):
    rewards, actions, oms, mus, std = import_data(results)
    outcome = get_outcome(rewards, actions)

    est_prob = np.sum(outcome==2,axis=1)/len(outcome[0,:])
    check_prob = np.sum(outcome==4,axis=1)/len(outcome[0,:])
    tot_reward = np.sum(rewards,axis=1)
    
    #  Plot
    fig, axs = plt.subplots(6, 1, figsize=(12, 8), sharex=True)

    from matplotlib import colors
    #axs[0].pcolormesh(actions, cmap='binary')
    #axs[0].set_title('Actions')
    # use the cmap which has blue for negative and red for positive values

    #plot actions, color code them by action array with the code -1: "b", 1 "r", 2: "k", 4: "w" 
    cmap = colors.ListedColormap(['b','r','k',"lightgreen"])
    bounds = [-0.5,0.5,1.5,2.5,3.5]
    norm = colors.BoundaryNorm(bounds, cmap.N)

    colors = ["b","r","k","w"]
    d = axs[0].pcolormesh(outcome, cmap=cmap, norm=norm)
    axs[0].grid(True)
    cb = plt.colorbar(d, ax = axs[0], orientation="vertical")
    cb.set_label('Action')
    cb.set_ticks([])
    plt.tight_layout()
    axs[0].grid(True)

    #mu
    dmu = mus
    dmu_plot = axs[1].pcolormesh(dmu, cmap="Reds", vmin=0, vmax=np.max(np.abs(dmu)))

    cb = plt.colorbar(dmu_plot, ax = axs[1], orientation="vertical")
    cb.set_label('Estimate $\mu$')
    plt.tight_layout()
    plt.grid()


    #Ustd
    sig_plot = axs[2].pcolormesh(std, cmap="Reds", vmin=0, vmax=np.max(std))

    cb = plt.colorbar(sig_plot, ax = axs[2], orientation="vertical")
    cb.set_label('Uncertainty $\sigma$')
    plt.tight_layout()
    plt.grid()


    #real om
    dmu = oms 
    dmu_plot = axs[3].pcolormesh(dmu, cmap="bwr", vmin=-np.max(np.abs(dmu)), vmax=np.max(np.abs(dmu)))

    cb = plt.colorbar(dmu_plot, ax = axs[3], orientation="vertical")
    cb.set_label('Real $\omega$')
    plt.tight_layout()
    plt.grid()


    #error
    dom = oms - mus
    om_plot = axs[4].pcolormesh(dom, cmap="bwr", vmin=-np.max(np.abs(dom)), vmax=np.max(np.abs(dom)))

    cb = plt.colorbar(om_plot, ax = axs[4], orientation="vertical")
    cb.set_label('Estimation error')
    plt.tight_layout()
    axs[1].grid(True)


    #error
    dom = np.abs(oms) - np.abs(mus)
    om_plot = axs[5].pcolormesh(dom, cmap="bwr", vmin=-np.max(np.abs(dom)), vmax=np.max(np.abs(dom)))

    cb = plt.colorbar(om_plot, ax = axs[5], orientation="vertical")
    cb.set_label('Estimation error abs')
    plt.tight_layout()
    plt.title(string)
    axs[1].grid(True)
    plt.savefig("figures/games"+str(string)+".png")

def analyse_few_games2(results, string):
    rewards, actions, oms, mus, std = import_data(results)
    rewards_to_plot = np.zeros(rewards.shape)
    times = np.zeros(rewards.shape)
    rewards_to_plot[rewards<0] = -1  #0 - success, #-1 -failure, times...
    rewards_to_plot[rewards==1] = 1
    times[rewards==0] = actions[1][rewards==0]
    maxtime = np.max(times)
    rewards_to_plot[rewards_to_plot==0] = None
    times[times==0] = None

    #est_prob = np.sum(outcome==2,axis=1)/len(outcome[0,:])
    #check_prob = np.sum(outcome==4,axis=1)/len(outcome[0,:])
    #tot_reward = np.sum(rewards,axis=1)
    
    #  Plot
    fig, axs = plt.subplots(6, 1, figsize=(12, 8), sharex=True)

    from matplotlib import colors
    #axs[0].pcolormesh(actions, cmap='binary')
    #axs[0].set_title('Actions')
    # use the cmap which has blue for negative and red for positive values

    #plot rewards with -1 -> blue, 0-> red, and >1 -> colormap
    
    cmap_rewards = "bwr"
    cmap_times = "binary"

    #colors = ["b","r","k","w"]
    d = axs[0].pcolormesh(rewards_to_plot, cmap=cmap_rewards)
    d2 = axs[0].pcolormesh(times, cmap=cmap_times,vmax = maxtime*2)
    axs[0].grid(True)
    cb = plt.colorbar(d2, ax = axs[0], orientation="vertical")
    cb.set_label('Action')
    cb.set_ticks([])
    plt.tight_layout()
    axs[0].grid(True)

    #mu
    dmu = mus
    dmu_plot = axs[1].pcolormesh(dmu, cmap="Reds", vmin=0, vmax=np.max(np.abs(dmu)))

    cb = plt.colorbar(dmu_plot, ax = axs[1], orientation="vertical")
    cb.set_label('Estimate $\mu$')
    plt.tight_layout()
    plt.grid()


    #Ustd
    sig_plot = axs[2].pcolormesh(std, cmap="Reds", vmin=0, vmax=np.max(std))

    cb = plt.colorbar(sig_plot, ax = axs[2], orientation="vertical")
    cb.set_label('Uncertainty $\sigma$')
    plt.tight_layout()
    plt.grid()


    #real om
    dmu = oms 
    dmu_plot = axs[3].pcolormesh(dmu, cmap="bwr", vmin=-np.max(np.abs(dmu)), vmax=np.max(np.abs(dmu)))

    cb = plt.colorbar(dmu_plot, ax = axs[3], orientation="vertical")
    cb.set_label('Real $\omega$')
    plt.tight_layout()
    plt.grid()


    #error
    dom = oms - mus
    om_plot = axs[4].pcolormesh(dom, cmap="bwr", vmin=-np.max(np.abs(dom)), vmax=np.max(np.abs(dom)))

    cb = plt.colorbar(om_plot, ax = axs[4], orientation="vertical")
    cb.set_label('Estimation error')
    plt.tight_layout()
    axs[1].grid(True)


    #error
    dom = np.abs(oms) - np.abs(mus)
    om_plot = axs[5].pcolormesh(dom, cmap="bwr", vmin=-np.max(np.abs(dom)), vmax=np.max(np.abs(dom)))

    cb = plt.colorbar(om_plot, ax = axs[5], orientation="vertical")
    cb.set_label('Estimation error abs')
    plt.tight_layout()
    plt.title(string)
    axs[1].grid(True)
    plt.savefig("figures/games"+str(string)+".png")

def analyse_few_games3(results, string):
    rewards, actions, oms, mus, std = import_data(results)
    rewards_to_plot = np.zeros(rewards.shape)
    times = np.zeros(rewards.shape)
    rewards_to_plot[rewards<0] = -1  #0 - success, #-1 -failure, times...
    rewards_to_plot[rewards==1] = 1
    times[rewards==0] = actions[1][rewards==0]
    maxtime = np.max(times)
    rewards_to_plot[rewards_to_plot==0] = None
    times[times==0] = None

    #est_prob = np.sum(outcome==2,axis=1)/len(outcome[0,:])
    #check_prob = np.sum(outcome==4,axis=1)/len(outcome[0,:])
    #tot_reward = np.sum(rewards,axis=1)
    
    #  Plot
    fig, axs = plt.subplots(6, 1, figsize=(6, 6), sharex=True)
    plt.subplots_adjust(hspace=0.0)
    from matplotlib import colors
    #axs[0].pcolormesh(actions, cmap='binary')
    #axs[0].set_title('Actions')
    # use the cmap which has blue for negative and red for positive values

    #plot rewards with -1 -> blue, 0-> red, and >1 -> colormap
    for k in range(6):
        axs[k].set_yticks([0,1,2,3])


    cmap_rewards = "bwr"
    cmap_times = "binary"

    #colors = ["b","r","k","w"]
    d = axs[0].pcolormesh(rewards_to_plot, cmap=cmap_rewards)
    d2 = axs[0].pcolormesh(times, cmap=cmap_times,vmax = maxtime*2)
    axs[0].grid(True)
    cb = plt.colorbar(d2, ax = axs[0], orientation="vertical")
    cb.set_label('Est. time')
    cb.set_ticks([])
    plt.tight_layout()
    axs[0].grid(True)
    axs[0].set_ylabel("Repetitions")
    #mu
    dmu = mus
    
    dmu_plot = axs[1].pcolormesh(dmu, cmap="Reds", vmin=0, vmax=np.max(np.abs(dmu)))

    cb = plt.colorbar(dmu_plot, ax = axs[1], orientation="vertical")
    cb.set_label('Est. $\omega$')
    plt.tight_layout()
    axs[1].grid(True)
    axs[1].set_ylabel("Repetitions")


    #Ustd
    sig_plot = axs[2].pcolormesh(std, cmap="Reds", vmin=0, vmax=np.max(std))

    cb = plt.colorbar(sig_plot, ax = axs[2], orientation="vertical")
    cb.set_label('Uncertainty')
    plt.tight_layout()
    plt.grid()
    axs[2].grid(True)
    axs[2].set_ylabel("Repetitions")


    #real om
    dmu = oms 
    dmu_plot = axs[3].pcolormesh(dmu, cmap="bwr", vmin=-np.max(np.abs(dmu)), vmax=np.max(np.abs(dmu)))

    cb = plt.colorbar(dmu_plot, ax = axs[3], orientation="vertical")
    cb.set_label('Real $\omega$')
    axs[3].grid(True)
    plt.tight_layout()
    plt.grid()
    axs[3].set_ylabel("Repetitions")

    #error
    dom = oms - mus
    om_plot = axs[4].pcolormesh(dom, cmap="bwr", vmin=-np.max(np.abs(dom)), vmax=np.max(np.abs(dom)))

    cb = plt.colorbar(om_plot, ax = axs[4], orientation="vertical")
    cb.set_label('Est. error')
    plt.tight_layout()
    axs[4].grid(True)
    plt.ylabel("Repetitions")

    #error
    dom = np.abs(oms) - np.abs(mus)
    om_plot = axs[5].pcolormesh(dom, cmap="bwr", vmin=-np.max(np.abs(dom)), vmax=np.max(np.abs(dom)))

    cb = plt.colorbar(om_plot, ax = axs[5], orientation="vertical")
    cb.set_label('Est. error')
    plt.tight_layout()
    axs[5].grid(True)
    plt.savefig("figures/games"+str(string)+".png")
    plt.xlabel("Consequtive shots (time)")
    plt.ylabel("Repetitions")





def analyse_decisions(results, string):
    rewards, actions, oms, mus, std = import_data(results)    
    outcome = np.zeros(mus.shape)
    outcome[rewards==1] = 1 
    outcome[rewards<0] = 0
    outcome[rewards==0] = 2
    
    import matplotlib.colors as colors
    cmap = colors.ListedColormap(['b','r','w',"k"])
    bounds = [0,1,2,3]
    norm = colors.BoundaryNorm(bounds, cmap.N)
    c = outcome.flatten()
    y = std.flatten()
    x = mus.flatten()
    z = y

    print("Probability of estimation: ", np.sum(outcome==2)/len(outcome.flatten()))
    print("Probability of success: ", np.sum(outcome==1)/len(outcome.flatten()))
    print("Probability of failing: ", np.sum(outcome==0)/len(outcome.flatten()))
    
    print("Probability of success given flip: ", np.sum(outcome==1)/np.sum(outcome<2))



    plt.title("Actions")
    plt.scatter(x,z,c=c, marker=".", cmap = cmap, norm=norm, alpha=1, s=1)
    plt.legend()
    plt.xlabel("Estimated om")
    plt.ylabel("Estimated std")
    plt.grid()
    plt.yscale("log")

    plt.savefig("figures/decisions_"+str(string)+".png")
    
    plt.figure()
    plt.hist(x[np.where(c==0)],color="b", bins = 100, alpha=0.6, density=True)
    plt.hist(x[np.where(c==1)],color="r", bins = 100, alpha=0.6, density=True)
    plt.hist(x[np.where(c==2)],color="k", bins = 100,alpha=0.6, density=True)
    plt.hist(x[np.where(c==4)],color="g", bins = 100,alpha=0.6, density=True)
    plt.xlabel("Estimated om $\mu$")
    plt.savefig("figures/histx_"+str(string)+".png")
    plt.figure()
    plt.hist(z[np.where(c==0)],color="b",bins = 100,alpha=0.6, density=True)
    plt.hist(z[np.where(c==1)],color="r",bins = 100,alpha=0.6, density=True)
    plt.hist(z[np.where(c==2)],color="k", bins = 100,alpha=0.6, density=True)
    plt.hist(z[np.where(c==4)],color="g", bins = 100,alpha=0.6, density=True)
    plt.xlabel("Estimated $\sigma$")
    plt.savefig("figures/histy_"+str(string)+".png")



def analyse_time(results, string):
    plt.figure()
    rewards, actions, oms, mus, std = import_data(results)
   
    #cmap = colors.ListedColormap(['b','r','w',"k"])
    bounds = [0,1,2,3]
    #norm = colors.BoundaryNorm(bounds, cmap.N)
    c = actions[1].flatten()
    y = std.flatten()
    x = mus.flatten()
    z = y

    fig, ax = plt.subplots(4,1,figsize=(8,8))
    
    ax[0].hist(actions[1].flatten(), bins=11)
    ax[0].set_xlabel("Time")
    ax[0].set_ylabel("Number of estimations")



    a = ax[1].scatter(x,z,c=c, marker=".", alpha=0.5)
    ax[1].legend()
    ax[1].set_xlabel("Estimated om")
    ax[1].set_ylabel("Estimated std")
    ax[1].grid()
    ax[1].set_yscale("log")
    cb = plt.colorbar(a, ax=ax[1])

    #plt.savefig("figures/decisions_"+str(string)+".png")
    
    bins = ax[3].hist(x,bins=11)
    times = []
    for n,bin0 in enumerate(bins[1]):
        if n == len(bins[1])-1:
            break
        else:
            filtr = (x>bin0) * (x < bins[1][n+1])
            times.append(c[filtr])
    ax[2].violinplot(times, showmeans=True)
    
    bins = ax[3].hist(y,bins=11)
    times = []
    for n,bin0 in enumerate(bins[1]):
        if n == len(bins[1])-1:
            break
        else:
            filtr = (y>bin0) * (y < bins[1][n+1])
            times.append(c[filtr])
    ax[3].clear()
    ax[3].violinplot(times, showmeans=True)
    



    